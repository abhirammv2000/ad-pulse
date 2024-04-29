import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import Button from '@mui/material/Button';
import AddAdUnitDialog from '../AdUnitDialog'; // Assuming AddAdUnitDialog component is in a separate file
import { useParams } from 'react-router-dom';

const AdUnitPage = () => {
  const { PubId } = useParams();
  const [adUnits, setAdUnits] = useState([]);
  const [openDialog, setOpenDialog] = useState(false);

  const baseUrl = process.env.REACT_APP_API_BASE_URL;

  const fetchData = async () => {
    try {
      const response = await axios.get(`${baseUrl}/adunit/publisher/${PubId}`);
      setAdUnits(response.data);
    } catch (error) {
      console.error('Error fetching ad units:', error);
    }
  };

  useEffect(() => {
    fetchData();
  }, [PubId]);

  const handleSaveAdUnit = async (adUnitName, adUnitType, preferences) => {
    try {
      const data = {
        adunitname: adUnitName,
        adunittype: adUnitType,
        publisherid: PubId,
        adunitstate: "ACTIVE",
        createdby: "Admin",
        updatedby: "Admin",
        preference: preferences
      };
  
      await axios.post(`${baseUrl}/adunit`, data);
      fetchData();
      setOpenDialog(false);
    } catch (error) {
      console.error('Error adding ad unit:', error);
    }
  };

  const handleStateChange = (adUnitId, currentState) => {
    const nextState = currentState === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    axios.patch(`${baseUrl}/adunit?ad_unit_id=${adUnitId}&state=${nextState}`)
      .then(response => {
        console.log('State changed successfully:', response.data);
        fetchData();
      })
      .catch(error => {
        console.error('Error changing state:', error);
      });
  };
  

  return (
    <div>
      <Button 
      variant="contained" 
      onClick={() => setOpenDialog(true)}
      style={{ marginLeft: 600, marginTop:"40px", right: 0 }}>Add New Ad Unit</Button>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Ad Unit ID</TableCell>
            <TableCell>Ad Unit Name</TableCell>
            <TableCell>State</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {adUnits.map((adUnit) => (
            <TableRow key={adUnit.adUnitId}>
              <TableCell>{adUnit.adunitid}</TableCell>
              <TableCell>{adUnit.adunitname}</TableCell>
              <TableCell>
                <Button
                  variant="contained"
                  color={adUnit.adunitstate === 'ACTIVE' ? 'secondary' : 'primary'}
                  onClick={() => handleStateChange(adUnit.adunitid, adUnit.adunitstate)}
                >
                  {adUnit.adunitstate === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <AddAdUnitDialog open={openDialog} handleClose={() => setOpenDialog(false)} handleSave={handleSaveAdUnit} />
    </div>
  );
};

export default AdUnitPage;
