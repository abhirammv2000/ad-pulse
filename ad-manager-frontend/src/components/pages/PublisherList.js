import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import TextField from '@mui/material/TextField';
import axios from 'axios';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';


const PublisherPage = (props) => {
  const [open, setOpen] = useState(false);
  const [publisherName, setPublisherName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [publisherState, setPublisherState] = useState('active');
  const [publisherDomain, setPublisherDomain] = useState('');
  const [preferenceLanguage, setPreferenceLanguage] = useState('English');
  const [preferenceTimezone, setPreferenceTimezone] = useState('UTC');
  // Will delete after login page
  const [createdBy, setCreatedBy] = useState('Admin');
  const [createdAt, setCreatedAt] = useState('2022-03-18T15:30:00');
  const [updatedBy, setUpdatedBy] = useState('Admin');
  const [updatedAt, setUpdatedAt] = useState('2022-03-18T15:30:00');

  const [publishers, setPublishers] = useState([]);
  const [selectedPublisher, setSelectedPublisher] = useState({});

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };
  const handlePublisherClick = (publisher) => {
    setSelectedPublisher(publisher);
    setOpen(true);
  };

  const handleSave = () => {
    // Process or save the input values here
    const data = {
      publishername: publisherName,
      contactinfo: {
        email: contactEmail,
        phone: contactPhone
      },
      publisherstate: publisherState,
      publisherdomain: publisherDomain,
      createdby: createdBy,
      updatedby: updatedBy,
      createdat: createdAt,
      updatedat: updatedAt,
      preference: {
        language: preferenceLanguage,
        timezone: preferenceTimezone
      }
    };
    axios.post('http://localhost:5000/publisher', data)
      .then(response => {
        console.log('Data sent successfully:', response.data);
        // Reset input fields
        setPublisherName('');
        setContactEmail('');
        setContactPhone('');
        setPublisherState('active');
        setPublisherDomain('');
        setPreferenceLanguage('English');
        setPreferenceTimezone('UTC');
        handleClose();
      })
      .catch(error => {
        console.error('Error sending data:', error);
        // Handle error appropriately
      });
  };

  return (
    <div style={{ position: 'absolute', top: '50px', right: '20px' }}>
      <Button variant="contained" onClick={handleClickOpen}>Add new publisher</Button>
  
      <Dialog open={open} onClose={handleClose}>
        <DialogTitle>Add New Publisher</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Please fill in the details of the new publisher.
          </DialogContentText>
          <TextField
            autoFocus
            margin="dense"
            label="Publisher Name"
            fullWidth
            value={publisherName}
            onChange={(e) => setPublisherName(e.target.value)}
          />
          <TextField
            margin="dense"
            label="Contact Email"
            fullWidth
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
          />
          <TextField
            margin="dense"
            label="Contact Phone"
            fullWidth
            value={contactPhone}
            onChange={(e) => setContactPhone(e.target.value)}
          />
          <TextField
            select
            margin="dense"
            label="Publisher State"
            fullWidth
            value={publisherState}
            onChange={(e) => setPublisherState(e.target.value)}
          >
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </TextField>
          <TextField
            margin="dense"
            label="Publisher Domain"
            fullWidth
            value={publisherDomain}
            onChange={(e) => setPublisherDomain(e.target.value)}
          />
          <TextField
            select
            margin="dense"
            label="Preference Language"
            fullWidth
            value={preferenceLanguage}
            onChange={(e) => setPreferenceLanguage(e.target.value)}
          >
            <option value="English">English</option>
            <option value="Spanish">Spanish</option>
            {/* Add more language options as needed */}
          </TextField>
          <TextField
            select
            margin="dense"
            label="Preference Timezone"
            fullWidth
            value={preferenceTimezone}
            onChange={(e) => setPreferenceTimezone(e.target.value)}
          >
            <option value="UTC">UTC</option>
            <option value="GMT">GMT</option>
            {/* Add more timezone options as needed */}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} color="primary">Cancel</Button>
          <Button onClick={handleSave} color="primary">Save</Button>
        </DialogActions>
      </Dialog>

      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Publisher Name</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {publishers.map((publisher) => (
            <TableRow key={publisher._id} onClick={() => handlePublisherClick(publisher)}>
              <TableCell>{publisher.publishername}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      
    </div>
  );
};

export default PublisherPage;
