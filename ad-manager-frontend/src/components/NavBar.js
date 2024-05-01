import React from 'react';
import { Link } from 'react-router-dom';
import { List, ListItem, ListItemText, IconButton } from '@mui/material';
import styled from '@emotion/styled';
import { Storage as StorageIcon, Assessment as AssessmentIcon, Home as HomeIcon, TrendingUp as TrendingUpIcon } from '@mui/icons-material';

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
