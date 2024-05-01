import React, { useEffect, useState } from 'react';
import { Table, TableHead, TableBody, TableRow, TableCell } from '@mui/material';
import styled from '@emotion/styled';
import Button from '@mui/material/Button';
const TableContainer = styled.div`
  margin-top: 20px;
  margin-left: 0;
  width: 100%;
`; 
function ReportsTable() {
    
  const baseUrl = process.env.REACT_APP_API_BASE_URL
  const [reports, setReports] = useState([]);
  useEffect(() => {
    fetchreports();
   
  }, []);
  const fetchreports = async () => {
     // Fetch data from baseurl:5000/reports
     fetch(`${baseUrl}/reports`)
     .then(response => response.json())
     .then(data => setReports(data))
     .catch(error => console.error('Error fetching reports:', error));
  }
  return (
    <div style={{width: "100%", marginLeft: 0}}>
    <Button 
        variant="contained" 
        onClick={fetchreports}
        style={{ marginLeft: 600, marginTop:"40px", right: 0 }}>
        Refresh
      </Button>
    <TableContainer>
    <Table>
      <TableHead>
        <TableRow>
          <TableCell> Ad ID</TableCell>
          <TableCell>Clicks</TableCell>
          <TableCell>Renders</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {reports.map(report => (
          <TableRow key={report._id}>
            <TableCell>{report._id}</TableCell>
            <TableCell>{report.click}</TableCell>
            <TableCell>{report.render}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
    </TableContainer>
    </div>
  );
}
export default ReportsTable;