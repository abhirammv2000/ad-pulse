import React, { useState } from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Dialog from '@mui/material/Dialog';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import axios from 'axios';

const CreativeCard = ({ open, handleClose, creatives, advertiserId, refreshCreatives }) => {
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [creativeName, setCreativeName] = useState('');
  const [creativeWidth, setCreativeWidth] = useState(0);
  const [creativeHeight, setCreativeHeight] = useState(0);
  const [selectedImage, setSelectedImage] = useState(null);

  const baseUrl = process.env.REACT_APP_API_BASE_URL;

  const handleAddDialogOpen = () => {
    setAddDialogOpen(true);
  };

  const handleAddDialogClose = () => {
    setAddDialogOpen(false);
    setCreativeName('');
    setCreativeWidth(0);
    setCreativeHeight(0);
    setSelectedImage(null);
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    setSelectedImage(file);
  };

  const handleAddCreative = async () => {
    try {
      const formData = new FormData();
      formData.append('cacheControl', '3600');
      formData.append('image', selectedImage);

      const uploadResponse = await axios.post(`${baseUrl}/creative/upload?filename=${creativeName}`, formData);

      const imageUrl = uploadResponse.data.image_url;

      const data = {
        advertiserid: advertiserId,
        assets: [
          {
            height: creativeHeight,
            imageType: 'MAIN',
            imageURL: imageUrl,
            required: true,
            type: 'IMAGE',
            width: creativeWidth
          }
        ],
        creativename: creativeName,
        creativestate: 'ACTIVE',
        creativetype: 'Native',
        createdby: 'Admin',
        updatedby: 'Admin'
      };

      await axios.post(`${baseUrl}/creative`, data);

      refreshCreatives();
      // Close the add dialog
      handleAddDialogClose();
    } catch (error) {
      console.error('Error adding creative:', error);
      // Handle error appropriately
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth PaperProps={{ style: { maxHeight: '75vh' } }}>
      <Card>
        <CardContent style={{ height: '60vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: "20px", marginBottom: "20px" }}>
            <h2 style={{ textAlign: 'left', margin: 0 }}>Creatives</h2>
            <div>
            <Button variant='contained' onClick={handleAddDialogOpen} style={{ marginLeft: '20px' }}>Add Creative</Button>
            <Button variant='contained' onClick={handleClose} style={{ marginLeft: '20px' }}>Close</Button>
            </div>
        </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'left' }}>
            {creatives.map((creative, index) => (
              <div key={index} style={{ margin: '10px', textAlign: 'center', flexBasis: '25%' }}>
                <img src={creative.assets[0].imageURL} alt={creative.creativename} style={{ width: '200px', height: '150px' }} />
                <p>{creative.creativename}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Dialog open={addDialogOpen} onClose={handleAddDialogClose}>
        <DialogTitle>Add Creative</DialogTitle>
        <DialogContent>
          <TextField
            label="Creative Name"
            value={creativeName}
            onChange={(e) => setCreativeName(e.target.value)}
            fullWidth
            margin="normal"
          />
          <TextField
            type='number'
            label="Width"
            value={creativeWidth}
            onChange={(e) => setCreativeWidth(parseInt(e.target.value))}
            fullWidth
            margin="normal"
          />
          <TextField
            type='number'
            label="Height"
            value={creativeHeight}
            onChange={(e) => setCreativeHeight(parseInt(e.target.value))}
            fullWidth
            margin="normal"
          />
          <TextField
            type="file"
            label="Select Image"
            onChange={handleImageChange}
            fullWidth
            margin="normal"
            InputLabelProps={{ shrink: true }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleAddDialogClose}>Cancel</Button>
          <Button onClick={handleAddCreative}>Add</Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  );
};

export default CreativeCard;
