import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import { Container, Typography, Box } from '@mui/material'
import StockTable from "./components/StockTable"

function App() {
  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4 }}>
        <Typography variant="h4" gutterBottom>
          Stock Investment Planner
        </Typography>

        <Typography variant="body1" color="text.secondary">
          Medium-term stock screener UI
        </Typography>

        <StockTable />
      </Box>
    </Container>
  )
}

export default App;

