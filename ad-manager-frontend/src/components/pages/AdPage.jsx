import React, { useState, useCallback, useEffect } from 'react';
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
import { useParams } from 'react-router-dom';
import {Alert, FormControl, InputLabel, MenuItem, Select } from '@mui/material';
import { API_BASE_URL } from '../../config';
import { buildAdPayload } from '../../requests/adPayload';



const TableContainer = styled.div`
  margin-top: 20px;
  margin-left: 0;
  width: 100%;
`;


const AdPage = () => {

  const baseUrl = API_BASE_URL
  const { AdvId,CampId } = useParams();

  const [adName, setAdName] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [landingUrl, setLandingUrl] = useState('');
  const [totalBudget, setTotalBudget] = useState('');
  const [dailyBudget, setDailyBudget] = useState('');
  const [bidType, setBidType] = useState('');
  const [adType, setAdType] = useState('');
  const [adPriority, setAdPriority] = useState('');
  const [timeTargetting, setTimeTargetting] = useState([]);
  const [dayTargetting, setDayTargetting] = useState([]);
  const [adUnitTargetting, setAdUnitTargetting] = useState('');
  const [creativeid, setCreativeId] = useState('');
  const [adUnits, setAdUnits] = useState([]);
  const [creativeList, setCreativeList] = useState([]);
  const [bid, setBid] = useState('');


  const [open, setOpen] = useState(false);
  const [ads, setAds] = useState([]);
  const [saveError, setSaveError] = useState('');

  const handleClickOpen = () => {
    setSaveError('');
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };


  const handleSave = () => {
    // An ad with no flight dates is stored but can never serve, so ask for them here.
    if (!startDate || !endDate) {
      setSaveError('Start and end dates are required.');
      return;
    }

    const data = buildAdPayload({
      adName,
      adPriority,
      adType,
      creativeId: creativeid,
      startDate,
      endDate,
      landingUrl,
      adUnit: adUnitTargetting,
      bidType,
      bid,
      dailyBudget,
      totalBudget,
      hours: timeTargetting,
      days: dayTargetting,
    }, CampId, AdvId);

    axios.post(`${baseUrl}/ad`, data)
      .then(() => {
        setAdName('');
        setStartDate('');
        setEndDate('');
        setLandingUrl('');
        setTotalBudget('');
        setDailyBudget('');
        setBidType('');
        setBid('');
        setAdType('');
        setAdPriority('');
        setTimeTargetting([]);
        setDayTargetting([]);
        setAdUnitTargetting('');
        setCreativeId('');
        fetchAds();
        handleClose();
      })
      .catch(error => {
        console.error('Error sending data:', error);
        // The manager says which field is wrong, so show its message.
        setSaveError(error.response?.data?.error || 'The ad could not be saved.');
      });
  };

  const fetchAds = useCallback(() => {
    axios.get(`${baseUrl}/ad/advertiser/${AdvId}/campaign/${CampId}`)
      .then(response => {
        setAds(response.data);
      })
      .catch(error => {
        console.error('Error fetching ads:', error);
      });
  }, [baseUrl, AdvId, CampId]);

  const fetchAdUnits = useCallback(() => {
    axios.get(`${baseUrl}/adunit`)
        .then(response => {
            setAdUnits(response.data);
        })
        .catch(error => {
            console.error('Error fetching ad units:', error);
        });
    }, [baseUrl]);

    const fetchCreativeList = useCallback(() => {
        axios.get(`${baseUrl}/creative`)
            .then(response => {
                setCreativeList(response.data);
            })
            .catch(error => {
                console.error('Error fetching creative list:', error);
            });
    }, [baseUrl]);

  useEffect(() => {
    fetchAds();
    fetchAdUnits();
    fetchCreativeList();
  }, [fetchAds, fetchAdUnits, fetchCreativeList]);

  const handleStateChange = (adId, currentState) => {
    const nextState = currentState === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    axios.patch(`${baseUrl}/ad?ad_id=${adId}&state=${nextState}`)
      .then(() => {
        fetchAds();
      })
      .catch(error => {
        console.error('Error changing state:', error);
      });
  };

  // The ad server compares these with the hour in UTC, which runs from 0 to 23.
  const timeOptions = Array.from({ length: 24 }, (_, index) => index);
  const dayOptions = Array.from({ length: 7 }, (_, index) => index + 1);

  return (
    <div style={{width: "100%", marginLeft: 0}}> 
        <Button 
        variant="contained" 
        onClick={handleClickOpen}
        style={{ marginLeft: 900, marginTop:"40px", right: 0 }}>
        Add new Ad
      </Button>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Ad ID</TableCell>
              <TableCell>Ad Name</TableCell>
              <TableCell>State</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {ads.map((ad) => (
              <TableRow key={ad._id} >
                <TableCell><Link to={`/inventory/${ad.adid}`}>{ad.adid}</Link></TableCell>
                <TableCell>{ad.adname}</TableCell>
                <TableCell>
                  <Button
                    variant="contained"
                    color={ad.adstate === 'ACTIVE' ? 'secondary' : 'primary'}
                    onClick={() => handleStateChange(ad.adid, ad.adstate)}
                  >
                    {ad.adstate === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={open} onClose={handleClose}>
        <DialogTitle>Add New Ad</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Please fill in the details of the new ad.
          </DialogContentText>
          {saveError && <Alert severity="error" style={{ marginTop: 10 }}>{saveError}</Alert>}
          {/* <TextField
              margin="dense"
              label="Ad Unit Targeted"
              fullWidth
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
            /> */}

            <TextField
                margin="dense"
                label="Ad Name"
                fullWidth
                value={adName}
                onChange={(e) => setAdName(e.target.value)}
            />
            <TextField style={{ margin: '10px 10px 10px 0'}}
            id="datePicker"
            label="Start Date"
            type="datetime-local"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            InputLabelProps={{
              shrink: true,
            }}
            />
            <TextField style={{margin: '10px 10px 10px 0'}}
            id="datePicker"
            label="End Date"
            type="datetime-local"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            InputLabelProps={{
              shrink: true,
            }}
            />
            <TextField
                margin="dense"
                label="Ad priority"
                type="number"
                fullWidth
                value={adPriority}
                onChange={(e) => setAdPriority(e.target.value)}
            />
            <FormControl fullWidth>
                <InputLabel id="ad-type-label">Ad Type</InputLabel>
                <Select
                    labelId="ad-type-label"
                    id="ad-type-select"
                    value={adType}
                    onChange={(e) => setAdType(e.target.value)}
                >
                    <MenuItem value="GUARANTEED">Guaranteed</MenuItem>
                    <MenuItem value="NON_GUARANTEED">Non-Guaranteed</MenuItem>
                    <MenuItem value="PROMOTIONAL">Promotional</MenuItem>
                </Select>
            </FormControl>
            
            <FormControl fullWidth>
                <InputLabel id="bid-type-label">Bid Type</InputLabel>
                <Select
                    labelId="bid-type-label"
                    id="bid-type-select"
                    value={bidType}
                    onChange={(e) => setBidType(e.target.value)}
                >
                    <MenuItem value="CPM">CPM</MenuItem>
                    <MenuItem value="CPC">CPC</MenuItem>
                </Select>
            </FormControl>
            <TextField
                margin="dense"
                label="Bid (USD)"
                type="number"
                fullWidth
                value={bid}
                onChange={(e) => setBid(e.target.value)}
            />
            <TextField
                margin="dense"
                label="Total Budget (USD)"
                type="number"
                fullWidth
                value={totalBudget}
                onChange={(e) => setTotalBudget(e.target.value)}
            />
            <TextField
                margin="dense"
                label="Daily Budget (USD)"
                type="number"
                fullWidth
                value={dailyBudget}
                onChange={(e) => setDailyBudget(e.target.value)}
            />
            <FormControl fullWidth>
                <InputLabel id="creative">Creative</InputLabel>
                <Select
                    labelId="creative"
                    id="creative"
                    margin="dense"
                    value={creativeid}
                    onChange={(e) => setCreativeId(e.target.value)}
                >
                    {creativeList.map((unit) => (
                    <MenuItem key={unit} value={unit.creativeid}>
                        {unit.creativename}
                    </MenuItem>
                    ))}
                </Select>
            </FormControl>
            <TextField
                margin="dense"
                label="Landing URL"
                fullWidth
                value={landingUrl}
                onChange={(e) => setLandingUrl(e.target.value)}
            />
            <FormControl fullWidth>
                <InputLabel id="ad-unit-targeted-label">Ad Unit Targeted</InputLabel>
                <Select
                    labelId="ad-unit-targeted-label"
                    id="ad-unit-targeted-select"
                    margin="dense"
                    value={adUnitTargetting}
                    onChange={(e) => setAdUnitTargetting(e.target.value)}
                >
                    {adUnits.map((unit) => (
                    <MenuItem key={unit} value={unit.adunitid}>
                        {unit.adunitname}
                    </MenuItem>
                    ))}
                </Select>
            </FormControl>
            <FormControl fullWidth>
                <InputLabel id="time-targeting-label">Hours (UTC)</InputLabel>
                <Select
                labelId="time-targeting-label"
                id="time-targeting-select"
                multiple
                value={timeTargetting}
                onChange={(e) => setTimeTargetting(e.target.value)}
                renderValue={(selected) => selected.join(', ')}
                >
                {timeOptions.map((hour) => (
                    <MenuItem key={hour} value={hour}>
                    {hour}
                    </MenuItem>
                ))}
                </Select>
            </FormControl>

            <FormControl fullWidth style={{marginTop: 10}}>
                <InputLabel id="day-targeting-label">Day Targeting</InputLabel>
                <Select
                labelId="day-targeting-label"
                id="day-targeting-select"
                multiple
                value={dayTargetting}
                onChange={(e) => setDayTargetting(e.target.value)}
                renderValue={(selected) => selected.join(', ')}
                >
                {dayOptions.map((day) => (
                    <MenuItem key={day} value={day}>
                    {day}
                    </MenuItem>
                ))}
                </Select>
            </FormControl>

            
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClose} color="primary">Cancel</Button>
            <Button onClick={handleSave} color="primary">Save</Button>
          </DialogActions>
        </Dialog>
      </div>
    );
  };
  
  export default AdPage; 
