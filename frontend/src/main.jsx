import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import { CompanyProvider } from './contexts/CompanyContext';
import { PermissionProvider } from './contexts/PermissionContext';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <CompanyProvider>
        <PermissionProvider>
          <App />
        </PermissionProvider>
      </CompanyProvider>
    </AuthProvider>
  </React.StrictMode>,
);
