import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import CreativeCard from '../CreativeCard';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TextField from '@mui/material/TextField';
import Paper from '@mui/material/Paper';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import axios from 'axios';
import { useParams } from 'react-router-dom';
import { Link } from 'react-router-dom';

const CampaignsPage = () => {
  const baseUrl = process.env.REACT_APP_API_BASE_URL;
  const { AdvId } = useParams();

  const [campaigns, setCampaigns] = useState([]);
  const [creatives, setCreatives] = useState([]);
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [openCreatives, setOpenCreatives] = useState(false);
  const [openAddCampaignDialog, setOpenAddCampaignDialog] = useState(false);


  const [campaignName, setCampaignName] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [totalBudget, setTotalBudget] = useState('');
  const [dailyBudget, setDailyBudget] = useState('');


  const fetchCampaigns = () => {
    axios.get(`${baseUrl}/campaign/advertiser/${AdvId}`)
      .then(response => {
        setCampaigns(response.data);
      })
      .catch(error => {
        console.error('Error fetching campaigns:', error);
      });
  };

  const fetchCreatives = () => {
    axios.get(`${baseUrl}/creative/advertiser/${AdvId}`)
      .then(response => {
        setCreatives(response.data);
      })
      .catch(error => {
        console.error('Error fetching creatives:', error);
      });
  };

  useEffect(() => {
    fetchCampaigns();
  }, [AdvId]);

  const handleViewCreatives = (campaignId) => {
    setSelectedCampaign(campaignId);
    fetchCreatives();
    setOpenCreatives(true);
  };

  const handleCloseCreatives = () => {
    setOpenCreatives(false);
  };

  const handleAddCampaign = () => {
    setOpenAddCampaignDialog(true);
  };

  const handleCloseAddCampaignDialog = () => {
    setOpenAddCampaignDialog(false);
  };

  const handleSave = () => {
    // Process or save the input values here
    const data = {
      campaignname: campaignName,
      advertiserid: AdvId,
      startdate: startDate,
      enddate: endDate,
      budget: {
        totalbudget: totalBudget,
        dailybudget: dailyBudget
      },
      createdby: 'Admin',
      updatedby: 'Admin',
    };
    axios.post(`${baseUrl}/campaign`, data)
      .then(response => {
        console.log('Data sent successfully:', response.data);
        // Reset input fields
        setCampaignName('');
        setStartDate('');
        setEndDate('');
        setTotalBudget('');
        setDailyBudget('');
        fetchCampaigns();
        handleCloseAddCampaignDialog();
        
      })
      .catch(error => {
        console.error('Error sending data:', error);
        // Handle error appropriately
      });
  };

  const handleStateChange = (campaignid, currentState) => {
    const nextState = currentState === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    axios.patch(`${baseUrl}/campaign?campaign_id=${campaignid}&state=${nextState}`)
      .then(response => {
        console.log('State changed successfully:', response.data);
        fetchCampaigns();
      })
      .catch(error => {
        console.error('Error changing state:', error);
      });
  };

  return (
    <div>
      <Button 
        variant="contained" 
        onClick={() => handleViewCreatives()}
        style={{ marginLeft: 900, marginTop:"40px", right: 0 }}>
        View Creatives
      </Button>

      <Button 
        variant="contained" 
        onClick={() => handleAddCampaign()}
        style={{ marginLeft: "20px", marginTop:"40px", right: 0 }}>
        Add Campaign
      </Button>

      <TableContainer component={Paper} style={{ marginTop: 20 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Campaign ID</TableCell>
              <TableCell>Campaign Name</TableCell>
              <TableCell>State</TableCell>
              {/* Add more campaign fields as needed */}
            </TableRow>
          </TableHead>
          <TableBody>
            {campaigns.map((campaign) => (
              <TableRow key={campaign.campaignid}>
                {/* <TableCell>{campaign.campaignid}</TableCell> */}
                <TableCell><Link to={`/demand/${AdvId}/campaign/${campaign.campaignid}`}>{campaign.campaignid}</Link></TableCell>
                <TableCell>{campaign.campaignname}</TableCell>
                <TableCell>
                  <Button
                    variant="contained"
                    color={campaign.campaignstate === 'ACTIVE' ? 'secondary' : 'primary'}
                    onClick={() => handleStateChange(campaign.campaignid, campaign.campaignstate)}
                  >
                    {campaign.campaignstate === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                  </Button>
                </TableCell>
                {/* Add more campaign fields as needed */}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      
      <CreativeCard open={openCreatives} handleClose={handleCloseCreatives} creatives={creatives} advertiserId={AdvId} refreshCreatives={fetchCreatives} />

      <Dialog open={openAddCampaignDialog} onClose={handleCloseAddCampaignDialog}>
        <DialogTitle>Add New Campaign</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Please fill in the details of the new campaign.
          </DialogContentText>
          {/* Add form fields for adding a new campaign */}
          <TextField
            autoFocus
            margin="dense"
            label="Campaign Name"
            fullWidth
            value={campaignName}
            onChange={(e) => setCampaignName(e.target.value)}
            />
            <TextField style={{ margin: '10px 10px 10px 0'}}
            id="datePicker"
            label="Start Date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            InputLabelProps={{
              shrink: true,
            }}
            />
            <TextField style={{margin: '10px 10px 10px 0'}}
            id="datePicker"
            label="End Date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            InputLabelProps={{
              shrink: true,
            }}
            />
            
            <TextField
              autoFocus
              margin="dense"
              label="Total Budget"
              fullWidth
              value={totalBudget}
              onChange={(e) => setTotalBudget(e.target.value)}
            />
            <TextField
              autoFocus
              margin="dense"
              label="Daily Budget"
              fullWidth
              value={dailyBudget}
              onChange={(e) => setDailyBudget(e.target.value)}
            />
            
          
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseAddCampaignDialog} color="primary">
            Cancel
          </Button>
          <Button onClick={handleSave} color="primary">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default CampaignsPage;
