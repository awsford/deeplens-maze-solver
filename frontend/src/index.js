import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './components/App';

import { Amplify, Auth } from 'aws-amplify';
import { AWSIoTProvider } from '@aws-amplify/pubsub';

import 'bootstrap/dist/css/bootstrap.css';
import './styles/index.css';
import '@aws-amplify/ui-react/styles.css';

import awsExports from './aws-exports';

awsExports.Storage = {
  region: 'eu-central-1',
  bucket: ''
}

Amplify.configure(awsExports);

Amplify.addPluggable(new AWSIoTProvider({
  aws_pubsub_region: 'eu-central-1',
  aws_pubsub_endpoint: 'wss://a2kjzb9cqfne4f-ats.iot.eu-central-1.amazonaws.com/mqtt',
}));

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
