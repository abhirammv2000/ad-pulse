import React, { useState } from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';

const AddAdUnitDialog = ({ open, handleClose, handleSave }) => {
  const [adUnitName, setAdUnitName] = useState('');
  const [adUnitType, setAdUnitType] = useState('');
  const [preferences, setPreferences] = useState({});

  const handlePreferencesChange = (e) => {
    const { name, value } = e.target;
    setPreferences(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  return (
    <Dialog open={open} onClose={handleClose}>
      <DialogTitle>Add New Ad Unit</DialogTitle>
      <DialogContent>
        <DialogContentText>
          Please fill in the details of the new ad unit.
        </DialogContentText>
        <TextField
          autoFocus
          margin="dense"
          label="Ad Unit Name"
          fullWidth
          value={adUnitName}
          onChange={(e) => setAdUnitName(e.target.value)}
        />
        <TextField
          select
          margin="dense"
          label="Ad Unit Type"
          fullWidth
          value={adUnitType}
          onChange={(e) => setAdUnitType(e.target.value)}
        >
          <MenuItem value="STANDARD">Standard</MenuItem>
          <MenuItem value="VIDEO">Video</MenuItem>
          <MenuItem value="BANNER">Banner</MenuItem>
          {/* Add more ad unit type options as needed */}
        </TextField>
        <TextField
          name="blockedCategories"
          margin="dense"
          label="Blocked Categories"
          fullWidth
          value={preferences.blockedCategories || ''}
          onChange={handlePreferencesChange}
        />
        <TextField
          name="blockedApps"
          margin="dense"
          label="Blocked Apps"
          fullWidth
          value={preferences.blockedApps || ''}
          onChange={handlePreferencesChange}
        />
        {/* Add more preference fields as needed */}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} color="primary">Cancel</Button>
        <Button onClick={() => handleSave(adUnitName, adUnitType, preferences)} color="primary">Save</Button>
      </DialogActions>
    </Dialog>
  );
};

export default AddAdUnitDialog;
