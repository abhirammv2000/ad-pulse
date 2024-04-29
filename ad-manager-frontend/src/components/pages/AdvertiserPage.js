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
import styled from '@emotion/styled';
import { Link } from 'react-router-dom';
import {
    Select,
    MenuItem,
  } from '@material-ui/core';
  import InputLabel from '@mui/material/InputLabel';



const TableContainer = styled.div`
  margin-top: 20px;
  margin-left: 0;
  width: 100%;
`;


const AdvertiserPage = (props) => {

  const baseUrl = process.env.REACT_APP_API_BASE_URL

  const [open, setOpen] = useState(false);
  const [advertiserName, setAdvertiserName] = useState('');
  const [industry, setIndustry] = useState('');
  const [brands, setBrands] = useState([]);
  const [contactName, setContactName] = useState('');
  const [contactAddress, setContactAddress] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [advertiserType, setAdvertiserType] = useState('');
  // Will delete after login page
  const [createdBy, setCreatedBy] = useState('Admin');
  const [createdAt, setCreatedAt] = useState('2022-03-18T15:30:00');
  const [updatedBy, setUpdatedBy] = useState('Admin');
  const [updatedAt, setUpdatedAt] = useState('2022-03-18T15:30:00');

  const [advertisers, setAdvertisers] = useState([]);
  const [selectedAdvertiser, setSelectedAdvertiser] = useState({});

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleAdvertiserClick = (advertiser) => {
    setSelectedAdvertiser(advertiser);
    setOpen(true);
  };

  const handleSave = () => {
    // Process or save the input values here
    const data = {
        advertisername: advertiserName,
        industry: industry,
        brands: brands,
        contactinfo: {
          name: contactName,
          address: contactAddress,
          email: contactEmail,
          phone: contactPhone
        },
        advertiseryype: advertiserType,
        createdby: createdBy,
        updatedby: updatedBy,
        createdat: createdAt,
        updatedat: updatedAt,
        
    };
    axios.post(`${baseUrl}/advertiser`, data)
      .then(response => {
        console.log('Data sent successfully:', response.data);
        // Reset input fields
        setAdvertiserName('');
        setIndustry('');
        setBrands([]);
        setContactName('');
        setContactAddress('');
        setContactEmail('');
        setContactPhone('');
        setAdvertiserType('');
        fetchAdvertisers();
        handleClose();
      })
      .catch(error => {
        console.error('Error sending data:', error);
        // Handle error appropriately
      });
  };

  const fetchAdvertisers = () => {
    axios.get(`${baseUrl}/advertiser`)
      .then(response => {
        setAdvertisers(response.data);
      })
      .catch(error => {
        console.error('Error fetching advertisers:', error);
      });
  };

  useEffect(() => {
    fetchAdvertisers();
  }, []); // Empty dependency array to fetch data only once on component mount

  const handleStateChange = (advertiserId, currentState) => {
    const nextState = currentState === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    axios.patch(`${baseUrl}/advertiser?advertiser_id=${advertiserId}&state=${nextState}`)
      .then(response => {
        console.log('State changed successfully:', response.data);
        fetchAdvertisers();
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
        Add new Advertiser
      </Button>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Advertiser ID</TableCell>
              <TableCell>Advertiser Name</TableCell>
              <TableCell>State</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {advertisers.map((advertiser) => (
              <TableRow key={advertiser._id} >
                <TableCell><Link to={`/demand/${advertiser.advertiserid}`}>{advertiser.advertiserid}</Link></TableCell>
                <TableCell>{advertiser.advertisername}</TableCell>
                <TableCell>
                  <Button
                    variant="contained"
                    color={advertiser.advertiserstate === 'ACTIVE' ? 'secondary' : 'primary'}
                    onClick={() => handleStateChange(advertiser.advertiserid, advertiser.advertiserstate)}
                  >
                    {advertiser.advertiserstate === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={open} onClose={handleClose}>
        <DialogTitle>Add New Advertiser</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Please fill in the details of the new Advertiser.
          </DialogContentText>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <TextField
            autoFocus
            margin="dense"
            label="Advertiser Name"
            fullWidth
            value={advertiserName}
            onChange={(e) => setAdvertiserName(e.target.value)}
            InputLabelProps={{
              shrink: true,
            }}
            />
            <TextField
            autoFocus
            margin="dense"
            label="Industry"
            fullWidth
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            InputLabelProps={{
              shrink: true,
            }}
            />
            <TextField
              margin="dense"
              label="Contact Name"
              fullWidth
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
              InputLabelProps={{
                shrink: true,
              }}
            />
            <TextField
              margin="dense"
              label="Contact Address"
              fullWidth
              value={contactAddress}
              onChange={(e) => setContactAddress(e.target.value)}
              InputLabelProps={{
                shrink: true,
              }}
            />
            <TextField
              margin="dense"
              label="Contact Phone"
              fullWidth
              value={contactPhone}
              onChange={(e) => setContactPhone(e.target.value)}
              InputLabelProps={{
                shrink: true,
              }}
            />
            <TextField
              margin="dense"
              label="Contact Email"
              fullWidth
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              InputLabelProps={{
                shrink: true,
              }}
            />
            <InputLabel id="advertiser-type-label">Type</InputLabel>
            <Select
              value={advertiserType}
              onChange={(e) => setAdvertiserType(e.target.value)}
              label="Type"
              fullWidth
              margin="dense"
              InputLabelProps={{
                shrink: true,
              }}
           >
              <MenuItem value="Paid">Paid</MenuItem>
              <MenuItem value="Unpaid">Unpaid</MenuItem>
            </Select>
          </div>
          </DialogContent>
        
          <DialogActions>
            <Button onClick={handleClose} color="primary">Cancel</Button>
            <Button onClick={handleSave} color="primary">Save</Button>
          </DialogActions>
        </Dialog>
      
      </div>
    )
  };
  
  export default AdvertiserPage; 
