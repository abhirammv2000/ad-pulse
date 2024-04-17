import React from 'react';
import { Link } from 'react-router-dom';
import { List, ListItem, ListItemText, ListItemIcon, IconButton } from '@mui/material';
import styled from '@emotion/styled';
import { Storage as StorageIcon, ExpandLess as ExpandLessIcon, ExpandMore as ExpandMoreIcon, Assessment as AssessmentIcon, Home as HomeIcon } from '@mui/icons-material';

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
  height: 100vh; /* Set height to 100% of viewport height */
  overflow-y: auto; /* Enable vertical scrolling if needed */
`;

const StyledList = styled(List)`
  padding-top: 40px; /* Adjust padding top to accommodate the fixed navbar */
`;

const SubList = styled(List)`
  padding-left: 20px;
`;

const NavBar = () => {
  const [isInventoryOpen, setIsInventoryOpen] = React.useState(false);
  const [isDemandOpen, setIsDemandOpen] = React.useState(false);

  const toggleInventory = () => {
    setIsInventoryOpen(!isInventoryOpen);
  };

  const toggleDemand = () => {
    setIsDemandOpen(!isDemandOpen);
  };

  return (
    <NavBarContainer>
      <ColorDiv>
        <IconButton component={Link} to="/" style={{ color: 'white' }}>
          <HomeIcon disablePadding/>
        </IconButton>
      </ColorDiv>
      <StyledList>
        <ListItem button onClick={toggleInventory}>
          <ListItemIcon>
            <StorageIcon style={{ color: 'white' }} />
          </ListItemIcon>
          <ListItemText primary="Inventory" />
          {isInventoryOpen ? <ExpandLessIcon style={{ color: 'white' }} /> : <ExpandMoreIcon style={{ color: 'white' }} />}
        </ListItem>
        {isInventoryOpen && (
          <SubList component="div" disablePadding>
            <ListItem button component={Link} to="/inventory/publisher">
              <ListItemText primary="Publisher" />
            </ListItem>
            <ListItem button component={Link} to="/inventory/adunit">
              <ListItemText primary="Ad Unit" />
            </ListItem>
          </SubList>
        )}
        <ListItem button onClick={toggleDemand}>
          <ListItemIcon>
            <StorageIcon style={{ color: 'white' }} />
          </ListItemIcon>
          <ListItemText primary="Demand" />
          {isDemandOpen ? <ExpandLessIcon style={{ color: 'white' }} /> : <ExpandMoreIcon style={{ color: 'white' }} />}
        </ListItem>
        {isDemandOpen && (
          <SubList component="div" disablePadding>
            <ListItem button component={Link} to="/demand/advertiser">
              <ListItemText primary="Advertiser" />
            </ListItem>
            <ListItem button component={Link} to="/demand/creative">
              <ListItemText primary="Creative" />
            </ListItem>
            <ListItem button component={Link} to="/demand/campaign">
              <ListItemText primary="Campaign" />
            </ListItem>
            <ListItem button component={Link} to="/demand/ad">
              <ListItemText primary="Ad" />
            </ListItem>
          </SubList>
        )}
        <ListItem button>
          <ListItemIcon>
            <AssessmentIcon style={{ color: 'white' }} />
          </ListItemIcon>
          <ListItemText primary="Reports" />
        </ListItem>
      </StyledList>
    </NavBarContainer>
  );
};

export default NavBar;
