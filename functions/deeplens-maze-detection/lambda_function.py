import json
from threading import Timer
import time
import awscam
import mo
import cv2
import uuid
import greengrasssdk
import numpy as np
import os
from botocore.session import Session
from datetime import datetime, timedelta

from local_display import LocalDisplay

TARGET_IMAGE_WIDTH = 600
TARGET_IMAGE_HEIGHT = 400
BUCKET_NAME = os.environ.get("BUCKET_NAME")

LOWER_GREEN = [30, 100, 40]
UPPER_GREEN = [90, 255, 255]
LOWER_WHITE = [0, 0, 100]
UPPER_WHITE = [100, 100, 255]
LOWER_PINK  = [360, 100, 100]
UPPER_PINK  = [200, 255, 255]

client = greengrasssdk.client('iot-data')
iot_topic = '$aws/things/{}/infer'.format(os.environ['AWS_IOT_THING_NAME'])

session = Session()
s3 = session.create_client('s3')

def lambda_handler(event, context):
    """Empty entry point to the Lambda function invoked from the edge."""
    return


def publish(msg = "", _type="json") -> None:
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

    try:
        while True:
            publish({ "status": "WORKING", "message": "staring loop, fetching frame in 2 seconds..." })
            time.sleep(2)
            payload = {}

            # Get a frame from the video stream
            ret, frame = awscam.getLastFrame()
            if not ret:
                publish({ "status": "ERROR", "message": "failed to get frame from stream" }, _type="json")
                raise Exception('Failed to get frame from the stream')

            time_now = datetime.now()

            """ ====== GREEN ====== """

            publish({ "status": "WORKING", "message": "Looking for green bounds..." })
            # mask for green and crop to bounding box
            mask = mask_frame(frame, LOWER_GREEN, UPPER_GREEN)
            contours = get_masked_contours(mask)

            if len(contours) == 0: continue

            contour = max(contours, key=cv2.contourArea)

            x, y, w, h = cv2.boundingRect(contour)

            # check that a green area has actually been found
            if w * h < TARGET_IMAGE_WIDTH * TARGET_IMAGE_HEIGHT:
                publish({ "status": "WORKING", "message": f"Green bounds too small - shape = {(w, h)}"})
                continue

            publish({ "status": "WORKING", "message": f"Found green bounds - shape = {(x, y, w, h)}"})

            if time_now <= cooldown:
                remaining = cooldown - time_now
                publish({ "status": "ON_COOLDOWN", "message": f"Loop on cooldown, seconds remaining: {remaining.seconds}"})
                time.sleep(1)
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

            publish({ "status": "WORKING", "message": f"Translated frame to flatten perspective - shape: {frame.shape}"})

            """ ====== WHITE ====== """
            # unique id for this detection
            idx = uuid.uuid4().hex

            publish({ "status": "WORKING", "id": str(idx), "message": f"Looking for white area within green bounds..."})
            #    mask for white and crop to bounding box
            mask = mask_frame(frame, LOWER_WHITE, UPPER_WHITE)
            contours = get_masked_contours(mask)

            if len(contours) == 0:
                publish({ "status": "WORKING", "id": str(idx), "message": "No white bounds found, continuing."})
                continue

            x, y, w, h = cv2.boundingRect(contour)

            # check that a white area has actually been found
            if w * h < TARGET_IMAGE_WIDTH * TARGET_IMAGE_HEIGHT:
                publish({ "status": "WORKING", "id": str(idx), "message": f"White bounds too small - shape = {(x, y)}"})
                continue

            publish({ "status": "WORKING", "id": str(idx), "message": f"Found white bounds - shape = {(x,y, w, h)}"})
            

            # downscale image for transfer and solve
            frame = cv2.resize(frame, (TARGET_IMAGE_WIDTH, TARGET_IMAGE_HEIGHT), interpolation=cv2.INTER_AREA)
            frame_copy = frame.copy()

            cv2.rectangle(frame_copy, (x, y), (x+w, y+h), (255, 0, 0), 4)
            cv2.imwrite(f"/tmp/{idx}_1.png", frame)

            """ ====== PINK ====== """

            publish({ "status": "WORKING", "id": str(idx), "message": f"Looking for maze start / end points..." })

            mask = mask_frame(frame, LOWER_PINK, UPPER_PINK)
            contours = get_masked_contours(mask)
            contours = sorted(contours, key=lambda x: cv2.contourArea(x), reverse=True)[:2]

            publish({ "status": "WORKING", "id": str(idx), "message": f"Found suitable start/stop points for solve" })

            # blank out the contours on the original frame
            cv2.drawContours(frame, contours, -1, (255, 255, 255), -1)
            # highlight the contours on the copied frame
            cv2.drawContours(frame_copy, contours, -1, (0, 0, 0), 4)
            
            rects = [cv2.boundingRect(contour) for contour in contours]
            cv2.imwrite(f"/tmp/{idx}_2.png", frame)

            """ ====== OUTPUT ====== """

            payload["image_dimensions"] = (frame.shape[1], frame.shape[0])
            payload["solve_start"] = find_centres(*rects[0])
            payload["solve_end"] = find_centres(*rects[1])
            payload["solve_resolution"] = 20

            # handle upload of frame to s3
            s3_key = f"{time.strftime('%Y%m%d')}/{idx}.png"
            frame_bytes = cv2.imencode('.png', frame)[1].tobytes()
            frame_copy_bytes = cv2.imencode('.png', frame_copy)[1].tobytes()
            s3.put_object(Body=frame_bytes, Bucket=BUCKET_NAME, Key=f"processed_frames/{s3_key}")
            s3.put_object(Body=frame_copy_bytes, Bucket=BUCKET_NAME, Key=f"original_frames/{s3_key}")

            s3_uri = f"s3://{BUCKET_NAME}/processed_frames/{s3_key}"
            publish({ "status": "COMPLETE", "id": str(idx), "message": f"maze image uploaded to bucket: - {s3_uri}" })
            payload["image_path"] = s3_uri

            # Send results back to IoT or output to video stream
            publish({ "status": "FOUND_MAZE", "id": str(idx), "payload": payload })

            # update local display
            local_display.set_frame_data(frame)

            cooldown = datetime.now() + timedelta(seconds=30)

    except Exception as e:
        publish({ "status": "ERROR", "message": f"Execution failed: {e}" })
    
    publish({ "status": "ERROR", "message": f"restarting thread in 5 seconds" })
    Timer(5, infinite_infer_run).start()

infinite_infer_run()

