import {React, useState} from 'react';

export const Reports = () => {
  return (
    <div className='reports'>
      <h1>Reports</h1>
    </div>
  );
};

export const ReportsOne = () => {
  const[name, setName] = useState('John');
  return (
    <div className='reports'>
      <h1>Reports/reports1 {name}</h1>
    </div>
  );
};

export const ReportsTwo = () => {
  return (
    <div className='reports'>
      <h1>Reports/reports2</h1>
    </div>
  );
};

export const ReportsThree = () => {
  return (
    <div className='reports'>
      <h1>hello world</h1>
    </div>
  );
};
