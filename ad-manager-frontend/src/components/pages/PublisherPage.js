import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import { Link } from 'react-router-dom';
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
import styled from '@emotion/styled';

const TableContainer = styled.div`
  margin-top: 20px;
  margin-left: 0;
  width: 100%;
`;


const PublisherPage = () => {

  const baseUrl = process.env.REACT_APP_API_BASE_URL

  const [open, setOpen] = useState(false);
  const [publisherName, setPublisherName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [publisherDomain, setPublisherDomain] = useState('');
  const [preferenceLanguage, setPreferenceLanguage] = useState('English');
  const [preferenceTimezone, setPreferenceTimezone] = useState('UTC');
  // Will delete after login page
  const createdBy = 'Admin';
  const updatedBy = 'Admin';

  const [publishers, setPublishers] = useState([]);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleSave = () => {
    // Process or save the input values here
    const data = {
      publishername: publisherName,
      contactinfo: {
        email: contactEmail,
        phone: contactPhone
      },
      publisherdomain: publisherDomain,
      createdby: createdBy,
      updatedby: updatedBy,
      preference: {
        language: preferenceLanguage,
        timezone: preferenceTimezone
      }
    };
    axios.post(`${baseUrl}/publisher`, data)
      .then(response => {
        console.log('Data sent successfully:', response.data);
        // Reset input fields
        setPublisherName('');
        setContactEmail('');
        setContactPhone('');
        setPublisherDomain('');
        setPreferenceLanguage('English');
        setPreferenceTimezone('UTC');
        fetchPublishers();
        handleClose();
      })
      .catch(error => {
        console.error('Error sending data:', error);
        // Handle error appropriately
      });
  };

  const fetchPublishers = () => {
    axios.get(`${baseUrl}/publisher`)
      .then(response => {
        setPublishers(response.data);
      })
      .catch(error => {
        console.error('Error fetching publishers:', error);
      });
  };

  useEffect(() => {
    fetchPublishers();
  }, []);

  const handleStateChange = (publisherId, currentState) => {
    const nextState = currentState === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    axios.patch(`${baseUrl}/publisher?publisher_id=${publisherId}&state=${nextState}`)
      .then(response => {
        console.log('State changed successfully:', response.data);
        fetchPublishers();
      })
      .catch(error => {
        console.error('Error changing state:', error);
      });
  };

  return (
    <div style={{width: "100%", marginLeft: 0}}>
      <Button 
        variant="contained" 
        onClick={handleClickOpen}
        style={{ marginLeft: 600, marginTop:"40px", right: 0 }}>
        Add new publisher
      </Button>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Publisher ID</TableCell>
              <TableCell>Publisher Name</TableCell>
              <TableCell>State</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {publishers.map((publisher) => (
              <TableRow key={publisher._id} >
                <TableCell><Link to={`/inventory/${publisher.publisherid}`}>{publisher.publisherid}</Link></TableCell>
                <TableCell>{publisher.publishername}</TableCell>
                <TableCell>
                  <Button
                    variant="contained"
                    color={publisher.publisherstate === 'ACTIVE' ? 'secondary' : 'primary'}
                    onClick={() => handleStateChange(publisher.publisherid, publisher.publisherstate)}
                  >
                    {publisher.publisherstate === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

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
      </div>
    )
  };
  
  export default PublisherPage; 
