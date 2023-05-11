import React, { useState, useEffect, useRef } from 'react'
import { withAuthenticator } from '@aws-amplify/ui-react';
import { Auth, PubSub, Storage } from 'aws-amplify';

import logo from "../images/logo.svg";
import "../styles/App.css";

import { Container, Card, Row } from "react-bootstrap";

function App() {
  const [mazes, setMazes] = useState([]);

  useEffect(() => {
    const sub = PubSub.subscribe('/maze-solver/events').subscribe({
      next: data => buildMazeArray(data),
      error: error => console.error(error),
      complete: () => console.log('Done'),
    });
    return () => {
      sub.unsubscribe();
    }
  }, []);

  const getToken = async () => (await Auth.currentSession()).getIdToken().getJwtToken();

  const buildMazeArray = async message => {
    const payload = message.value;

    // check whether maze is already loaded?

    // fetch each of the pictures in the payload
    const obj_keys = [ "raw", "processed", "skeleton", "solved" ]
    for (let obj_key of obj_keys) {
      const image = await fetchImage(payload[obj_key])
      payload[obj_key] = image
    }

    // add incoming maze to array
    setMazes(old => [payload, ...old]);
  }

  const fetchImage = async key => {
    const image = await Storage.get( key, {
      customPrefix: { public: '' },
      headers: { Authorization: `Bearer ${(await getToken())}` }
    });
    return image;
  }
  
  return (
    <Container className="wrapper">
      <div className="title row m-2 text-center">
        <h1>Maze Dashboard</h1>
      </div>
      <Container fluid>
        {
          mazes.length === 0
          ? 
            <div className="title row m-2 text-center">
              <h3>No mazes found</h3>
            </div>
          :
            mazes.map((maze, idx) => (
              <Row key={idx} xs={4} className="g-4 maze-row justify-content-center">
                <Card className="maze-card">
                  <Card.Title className="mb-2 text-muted text-center maze-card-title">Raw</Card.Title>
                  <Card.Img variant="top" src={maze.raw} height="300px" />
                </Card>
                <Card className="maze-card">
                  <Card.Title className="mb-2 text-muted text-center maze-card-title">Processed</Card.Title>
                  <Card.Img variant="top" src={maze.processed} height="300px" />
                </Card>
                <Card className="maze-card">
                  <Card.Title className="mb-2 text-muted text-center maze-card-title">Skeleton</Card.Title>
                  <Card.Img variant="top" src={maze.skeleton} height="300px" />
                </Card>
                <Card className="maze-card">
                  <Card.Title className="mb-2 text-muted text-center maze-card-title">Solved</Card.Title>
                  <Card.Img variant="top" src={maze.solved} height="300px" />
                </Card>
              </Row>
            ))
        }
      </Container>
    </Container>
  );
}

export default withAuthenticator(App);
