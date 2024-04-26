import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import axios from 'axios';
import { useParams } from 'react-router-dom';

const CampaignsPage = () => {
  const baseUrl = process.env.REACT_APP_API_BASE_URL;
  const { AdvId } = useParams();

  const [campaigns, setCampaigns] = useState([]);
  const [creatives, setCreatives] = useState([]);
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [openCreatives, setOpenCreatives] = useState(false);
  const [openAddCampaignDialog, setOpenAddCampaignDialog] = useState(false);

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

  return (
    <div>
      <Button 
        variant="contained" 
        onClick={() => handleViewCreatives()}
        style={{ marginRight: 10 }}>
        View Creatives
      </Button>

      <Button 
        variant="contained" 
        onClick={() => handleAddCampaign()}>
        Add Campaign
      </Button>

      <TableContainer component={Paper} style={{ marginTop: 20 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Campaign ID</TableCell>
              <TableCell>Campaign Name</TableCell>
              {/* Add more campaign fields as needed */}
            </TableRow>
          </TableHead>
          <TableBody>
            {campaigns.map((campaign) => (
              <TableRow key={campaign.id}>
                <TableCell>{campaign.id}</TableCell>
                <TableCell>{campaign.name}</TableCell>
                {/* Add more campaign fields as needed */}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openCreatives} onClose={handleCloseCreatives} maxWidth="md" fullWidth style={{height: "500px"}}>
        <Card>
          <CardContent>
            <Typography variant="h5" component="h2">
              Creatives
            </Typography>
            <TableContainer component={Paper} style={{ marginTop: 10 }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Creative ID</TableCell>
                    <TableCell>Creative Name</TableCell>
                    {/* Add more creative fields as needed */}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {creatives.map((creative) => (
                    <TableRow key={creative.id}>
                      <TableCell>{creative.creativeid}</TableCell>
                      <TableCell>{creative.creativename}</TableCell>
                      {/* Add more creative fields as needed */}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Dialog>

      <Dialog open={openAddCampaignDialog} onClose={handleCloseAddCampaignDialog}>
        <DialogTitle>Add New Campaign</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Please fill in the details of the new campaign.
          </DialogContentText>
          {/* Add form fields for adding a new campaign */}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseAddCampaignDialog} color="primary">
            Cancel
          </Button>
          <Button onClick={handleCloseAddCampaignDialog} color="primary">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default CampaignsPage;
