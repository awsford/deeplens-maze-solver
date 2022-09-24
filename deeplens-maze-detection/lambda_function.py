from datetime import datetime, timedelta
import json
from time import time
from typing import Any, Dict
import awscam
import mo
import cv2
import uuid
import greengrasssdk
import numpy as np
import os
from botocore.session import Session
from local_display import LocalDisplay

TARGET_IMAGE_WIDTH = 600
TARGET_IMAGE_HEIGHT = 400

client = greengrasssdk.client('iot-data')
iot_topic = '$aws/things/{}/infer'.format(os.environ['AWS_IOT_THING_NAME'])
bucket_name = ""

def lambda_handler(event, context):
    """Empty entry point to the Lambda function invoked from the edge."""
    return


def publish(msg = "", _type="message") -> None:
    if _type == "json":
        msg = json.dumps(msg)

    client.publish(topic=iot_topic, payload=msg)


def mask_frame(frame, hsv_lower, hsv_upper):
    hsvFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # detect the green bounds
    lower = np.array(hsv_lower, np.uint8)
    upper = np.array(hsv_upper, np.uint8)
    mask = cv2.inRange(hsvFrame, lower, upper)

    kernel = np.ones((5, 5), "uint8")
    mask = cv2.dilate(mask, kernel)
    return mask


def get_masked_contours(mask):
    _, thresh = cv2.threshold(mask, 40, 255, 0)
    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return contours


def find_centres(x, y, w, h):
    return [int(x + w/2), int(y + h/2)]


def infinite_infer_run():
    """ Run the DeepLens inference loop frame by frame"""

    local_display = LocalDisplay('480p')
    local_display.start()

    publish({ "status": "STARTING" }, _type="json")

    cooldown = datetime.now()

    while True:
        payload: Dict[Any, Any] = {}

        # Get a frame from the video stream
        ret, frame = awscam.getLastFrame()
        if not ret:
            publish({ "status": "ERROR", "message": "failed to get frame from stream" }, _type="json")
            raise Exception('Failed to get frame from the stream')

        time_now = datetime.now()

        """ ====== GREEN ====== """

        print(f"Looking for green bounds...")
        # mask for green and crop to bounding box
        mask = mask_frame(frame, [40, 40, 40], [70, 255, 255])
        contours = get_masked_contours(mask)
        contour = max(contours, key=cv2.contourArea)

        # check that a green area has actually been found
        if frame.shape[0] * frame.shape[1] < TARGET_IMAGE_WIDTH * TARGET_IMAGE_HEIGHT:
            publish({ "status": "WORKING", "message": f"Green bounds too small - shape = {frame.shape}"})
            continue

        publish({ "status": "WORKING", "message": f"Found green bounds - shape = {frame.shape}"})

        if time_now <= cooldown:
            continue

        """ ====== TRANSLATE ====== """
        # rotate image to longest axis of green bounds

        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        # set longest dimension as image width
        width = int(max(rect[1]))
        height = int(min(rect[1]))

        src_points = box.astype("float32")
        dst_points = np.array([[0, height-1],
                            [0, 0],
                            [width-1, 0],
                            [width-1, height-1]], dtype="float32")

        M = cv2.getPerspectiveTransform(src_points, dst_points)
        frame = cv2.warpPerspective(frame, M, (width, height))

        publish({ "status": "WORKING", "message": f"Translated frame to flatten perspective"})

        """ ====== WHITE ====== """

        publish({ "status": "WORKING", "message": f"Looking for white area within green bounds..."})
        #    mask for white and crop to bounding box
        mask = mask_frame(frame, [0, 0, 160], [255, 50, 255])
        contours = get_masked_contours(mask)
        contour = max(contours, key=cv2.contourArea)

        # check that a white area has actually been found
        if frame.shape[0] * frame.shape[1] < TARGET_IMAGE_WIDTH * TARGET_IMAGE_HEIGHT:
            publish({ "status": "WORKING", "message": f"White bounds too small - shape = {frame.shape}"})
            continue

        publish({ "status": "WORKING", "message": f"Found white bounds - shape = {frame.shape}"})

        # downscale image for transfer and solve
        frame = cv2.resize(
            frame, (TARGET_IMAGE_WIDTH, TARGET_IMAGE_HEIGHT), interpolation=cv2.INTER_AREA)

        """ ====== PINK ====== """

        publish({ "status": "WORKING", "message": f"Looking for maze start / end points..." })
        mask = mask_frame(frame, [360, 100, 100], [200, 255, 255])
        contours = get_masked_contours(mask)
        contours = sorted(
            contours, key=lambda x: cv2.contourArea(x), reverse=True)[:2]
        
        if len(contours != 2):
            publish({ "status": "ERROR", "message": f"Error finding start/stop points, {len(contours)} points found"})
            continue
        
        publish({ "status": "WORKING", "message": f"Found suitable start/stop points for solve" })

        cv2.drawContours(frame, contours, -1, (255, 255, 255), -1)
        rects = [cv2.boundingRect(contour) for contour in contours]

        """ ====== OUTPUT ====== """
        idx = uuid.uuid4().hex

        output_path = f"/tmp/{idx}.png"
        cv2.imwrite(output_path, frame)

        payload["image_path"] = output_path
        payload["image_dimensions"] = (frame.shape[1], frame.shape[0])
        payload["solve_start"] = find_centres(*rects[0])
        payload["solve_end"] = find_centres(*rects[1])
        payload["solve_resolution"] = 20
        
        # Send results back to IoT or output to video stream
        publish({ "status": "FOUND_MAZE", **payload })

        # update local display
        local_display.set_frame_data(frame)

        key = 'images/frame-' + time.strftime("%Y%m%d-%H%M%S") + '.jpg'
        session = Session()
        s3 = session.create_client('s3')

        _, jpg_data = cv2.imencode('.jpg', frame)
        result = s3.put_object(Body=jpg_data.tostring(), Bucket=bucket_name, Key=key)

        cooldown = datetime.now() + timedelta(seconds=10)

        time.sleep(0.5)
infinite_infer_run()