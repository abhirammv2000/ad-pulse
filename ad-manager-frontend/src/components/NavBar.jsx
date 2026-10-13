import React from 'react';
import { Link } from 'react-router-dom';
import { List, ListItem, ListItemText, IconButton } from '@mui/material';
import styled from '@emotion/styled';
// One import per icon. The package's index file pulls in every icon MUI has, which made the tests take minutes.
import StorageIcon from '@mui/icons-material/Storage';
import AssessmentIcon from '@mui/icons-material/Assessment';
import HomeIcon from '@mui/icons-material/Home';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';

const ColorDiv = styled.div`
  background-color: cornflowerblue;
  height: 40px;
  width: 100%;
  display: flex;
  align-items: center;
  padding-left: 20px;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 1000;
`;

const NavBarContainer = styled.div`
  background-color: cornflowerblue;
  height: 100vh;
  overflow-y: auto;
`;

const StyledList = styled(List)`
  padding-top: 40px;
`;

const NavBar = () => {
  return (
    <NavBarContainer>
      <ColorDiv>
        <IconButton component={Link} to="/" style={{ color: 'white', left: 0 }}>
          <HomeIcon/>
        </IconButton>
      </ColorDiv>
      <StyledList>
        <ListItem button component={Link} to="/inventory">
          <StorageIcon style={{ color: 'white' }} />
          <ListItemText primary="Inventory" />
        </ListItem>
        <ListItem button component={Link} to="/demand">
          <AssessmentIcon style={{ color: 'white' }} />
          <ListItemText primary="Demand" />
        </ListItem>
        <ListItem button component={Link} to="/report">
          <TrendingUpIcon style={{ color: 'white' }} />
          <ListItemText primary="Reports" />
        </ListItem>
      </StyledList>
    </NavBarContainer>
  );
};

export default NavBar;
