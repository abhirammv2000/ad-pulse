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
import { useParams } from 'react-router-dom';
import {FormControl, InputLabel, MenuItem, Select } from '@mui/material';



const TableContainer = styled.div`
  margin-top: 20px;
  margin-left: 0;
  width: 100%;
`;


const Ads = () => {

  const baseUrl = process.env.REACT_APP_API_BASE_URL
  const { AdvId,CampId } = useParams();
//   console.log("ad id",AdvId);
//   console.log("camp id",CampId);

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
    const [adUnitTargetting, setAdUnitTargetting] = useState([]);
    const [creativeid, setCreativeId] = useState('');


    const [adUnits, setAdUnits] = useState([]);
    const [creativeList, setCreativeList] = useState([]);


  const [open, setOpen] = useState(false);
  const [ads, setAds] = useState([]);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };



  // adId varchar PRIMARY KEY,
//   adName varchar,
//   campaignId varchar,
//   advertiserId varchar,
//   creativeId varchar, call api to get creative id
//   startDate timestamp,
//   endDate timestamp,
//   landingUrl varchar,
//   budget jsonb,
//   frequencyCaps sonb,
//   bidInfo jsonb, CPM,CPC,CPD
//   adType varchar, gaur, non-gaur, promo
//   adPriority int,
//   targetingInfo jsonb, drop down [1-14], [1-7]
//   createdAt timestamp,
//   updatedAt timestamp,
//   createdBy varchar,
//   updatedBy varchar,
//   adState varchar

  const handleSave = () => {
    // Process or save the input values here
    const data = {
        ad_unit_targeted: [adUnitTargetting],
        adname: adName,
        adpriority: adPriority,
        adtype: adType,
        campaignid: CampId,
        advertiserid: AdvId,
       creativeid: creativeid,
        startdate: startDate,
        enddate: endDate,
        adstate: "ACTIVE",
        landingurl: landingUrl,
        budget:{
            totalbudget: totalBudget,
            dailybudget: dailyBudget,
            currencycode: "USD",
        },
        bidinfo:{
            bidtype: bidType,
            bid: 1,
        },
        targetinginfo:{
            timetargeting:{
              type: "equal",
              values: timeTargetting
            },
            daytargeting:{
              type: "equal",
              values: dayTargetting
            }
        },

      }
    
    axios.post(`${baseUrl}/ad`, data)
      .then(response => {
        console.log('Data sent successfully:', response.data);
        // Reset input fields
        // setPublisherName('');
        // setContactEmail('');
        // setContactPhone('');
        // setPublisherDomain('');
        // setPreferenceLanguage('English');
        // setPreferenceTimezone('UTC');
        // fetchAds();
        // handleClose();
        setAdName('');
        setStartDate('');
        setEndDate('');
        setLandingUrl('');
        setTotalBudget('');
        setDailyBudget('');
        setBidType('');
        setAdType('');
        setAdPriority('');
        setTimeTargetting([]);
        setDayTargetting([]);
        setAdUnitTargetting([]);
        setCreativeId('');
        fetchAds();
        handleClose();
      })
      .catch(error => {
        console.error('Error sending data:', error);
        // Handle error appropriately
      });
  };

  const fetchAds = () => {
    axios.get(`${baseUrl}/ad`)
      .then(response => {
        setAds(response.data);
      })
      .catch(error => {
        console.error('Error fetching publishers:', error);
      });
  };

  const fetchAdUnits = () => {
    axios.get(`${baseUrl}/adunit`)
        .then(response => {
            setAdUnits(response.data);
        })
        .catch(error => {
            console.error('Error fetching ad units:', error);
        });
    };

    const fetchCreativeList = () => {
        axios.get(`${baseUrl}/creative`)
            .then(response => {
                setCreativeList(response.data);
            })
            .catch(error => {
                console.error('Error fetching creative list:', error);
            });
    };

  useEffect(() => {
    fetchAds();
    fetchAdUnits();
    fetchCreativeList();
  }, []);

  const handleStateChange = (publisherId, currentState) => {
    const nextState = currentState === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    axios.patch(`${baseUrl}/ad?ad_id=${publisherId}&state=${nextState}`)
      .then(response => {
        console.log('State changed successfully:', response.data);
        fetchAds();
      })
      .catch(error => {
        console.error('Error changing state:', error);
      });
  };

  const timeOptions = Array.from({ length: 24 }, (_, index) => index + 1);
  const dayOptions = Array.from({ length: 7 }, (_, index) => index + 1);

  return (
    <div style={{width: "100%", marginLeft: 0}}> 
        <Button 
        variant="contained" 
        onClick={handleClickOpen}
        style={{ marginLeft: 1000, marginTop:"40px", right: 0 }}>
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
                margin="dense"
                label="Ad priority"
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
                    <MenuItem value="NON_GUARANTEE">Non-Guaranteed</MenuItem>
                    <MenuItem value="PROMO">Promo</MenuItem>
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
                    <MenuItem value="CPD">CPD</MenuItem>
                </Select>
            </FormControl>
            <TextField
                margin="dense"
                label="Total Budget"
                fullWidth
                value={totalBudget}
                onChange={(e) => setTotalBudget(e.target.value)}
            />
            <TextField
                margin="dense"
                label="Daily Budget"
                fullWidth
                value={dailyBudget}
                onChange={(e) => setDailyBudget(e.target.value)}
            />
            <FormControl fullWidth>
                <InputLabel id="ad-unit-targeted-label">Ad Unit Targeted</InputLabel>
                <Select
                    labelId="ad-unit-targeted-label"
                    id="ad-unit-targeted-select"
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
                    <MenuItem key={unit} value={unit.adunitname}>
                        {unit.adunitname}
                    </MenuItem>
                    ))}
                </Select>
            </FormControl>
            <FormControl fullWidth>
                <InputLabel id="time-targeting-label">Time Targeting</InputLabel>
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
  
  export default Ads; 
