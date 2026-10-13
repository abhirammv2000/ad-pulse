import React, { useEffect, useState } from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import TextField from '@mui/material/TextField';
import { AUTH_REQUIRED_EVENT, getApiKey, setApiKey } from '../auth';

// Opens when the ad manager answers 401, asks for the API key, stores it for this tab and reloads so every
// page loads its data again with the key.
export default function ApiKeyDialog() {
  const [open, setOpen] = useState(false);
  const [rejected, setRejected] = useState(false);
  const [value, setValue] = useState('');

  useEffect(() => {
    const onAuthRequired = () => {
      // if a key was already stored, the manager has just refused it
      setRejected(Boolean(getApiKey()));
      setApiKey('');
      setOpen(true);
    };
    window.addEventListener(AUTH_REQUIRED_EVENT, onAuthRequired);
    return () => window.removeEventListener(AUTH_REQUIRED_EVENT, onAuthRequired);
  }, []);

  const submit = (event) => {
    event.preventDefault();
    const key = value.trim();
    if (!key) {
      return;
    }
    setApiKey(key);
    window.location.reload();
  };

  return (
    <Dialog open={open} PaperProps={{ component: 'form', onSubmit: submit }}>
      <DialogTitle>API key needed</DialogTitle>
      <DialogContent>
        <DialogContentText>
          {rejected
            ? 'The ad manager did not accept that key. Enter the key again.'
            : 'The ad manager asks for an API key. It is kept for this browser tab only.'}
        </DialogContentText>
        <TextField
          autoFocus
          fullWidth
          margin="dense"
          label="API key"
          type="password"
          autoComplete="off"
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
      </DialogContent>
      <DialogActions>
        <Button type="submit" variant="contained" disabled={!value.trim()}>
          Continue
        </Button>
      </DialogActions>
    </Dialog>
  );
}
