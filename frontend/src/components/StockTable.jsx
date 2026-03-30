import { useEffect, useState } from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  TableSortLabel,
  Box,
  Slider,
  Typography,
  IconButton,
  Collapse,
  CircularProgress,
  Alert,
  Select,//
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material"
import { Stack } from "@mui/material"
import ExpandMoreIcon from "@mui/icons-material/ExpandMore"

const API_URL = "http://127.0.0.1:8000/api/medium-term"

function getAdvice(score) {
  if (score >= 70) return { label: "Buy", color: "success" }
  if (score >= 50) return { label: "Watch", color: "warning" }
  return { label: "Avoid", color: "error" }
}

function getScoreBreakdown(score) {
  if (score >= 70) {
    return {
      trend: "Strong",
      momentum: "Strong",
      risk: "Low",
    }
  }

  if (score >= 50) {
    return {
      trend: "Moderate",
      momentum: "Moderate",
      risk: "Medium",
    }
  }

  if (score >= 30) {
    return {
      trend: "Weak",
      momentum: "Weak",
      risk: "Medium",
    }
  }

  return {
    trend: "Weak",
    momentum: "Weak",
    risk: "High",
  }
}


function StockTable() {
  const [stocks, setStocks] = useState([])
  const [order, setOrder] = useState("desc")
  const [minScore, setMinScore] = useState(0)
  const [limit, setLimit] = useState(20) //Pagination
  const [openRow, setOpenRow] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const url = `http://127.0.0.1:8000/api/medium-term?minScore=${minScore}&limit=${limit}`

    fetch(url)
      .then((res) => {
        if (!res.ok) {
          throw new Error("Failed to fetch data from backend")
        }
        return res.json()
      })
      .then((data) => {
        setStocks(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [minScore, limit])

  const handleSort = () => {
    setOrder((prev) => (prev === "asc" ? "desc" : "asc"))
  }

  const filteredAndSortedStocks = [...stocks]
    .filter((s) => s.score >= minScore)
    .sort((a, b) =>
      order === "asc" ? a.score - b.score : b.score - a.score
    )

  // ---------- UI STATES ----------
  if (loading) {
    return (
      <Box sx={{ mt: 6, textAlign: "center" }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading stock data…</Typography>
      </Box>
    )
  }

  if (error) {
    return (
      <Box sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    )
  }

  return (
    <>
      {/* Filter */}
      <Box sx={{ mt: 4, mb: 2 }}>
  <Stack
    direction={{ xs: "column", md: "row" }}
    spacing={3}
    alignItems="center"
  >
    {/* Limit dropdown */}
    <FormControl sx={{ minWidth: 140 }}>
      <InputLabel>Show</InputLabel>
      <Select
        value={limit}
        label="Show"
        onChange={(e) => setLimit(e.target.value)}
      >
        <MenuItem value={20}>Top 20</MenuItem>
        <MenuItem value={50}>Top 50</MenuItem>
        <MenuItem value={100}>Top 100</MenuItem>
      </Select>
    </FormControl>

    {/* Score filter */}
    <Box sx={{ flex: 1 }}>
      <Typography gutterBottom>
        Minimum Score: <b>{minScore}</b>
      </Typography>

      <Slider
        value={minScore}
        min={0}
        max={100}
        step={5}
        onChange={(e, value) => setMinScore(value)}
        valueLabelDisplay="auto"
      />
    </Box>
  </Stack>
</Box>


      {/* Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell />
              <TableCell><b>Symbol</b></TableCell>

              <TableCell sortDirection={order}>
                <TableSortLabel
                  active
                  direction={order}
                  onClick={handleSort}
                >
                  <b>Score</b>
                </TableSortLabel>
              </TableCell>

              <TableCell><b>Advice</b></TableCell>
            </TableRow>
          </TableHead>

          <TableBody>
            {filteredAndSortedStocks.map((row) => {
              const advice = getAdvice(row.score)
              const isOpen = openRow === row.symbol
              const breakdown = getScoreBreakdown(row.score)

              return (
                <>
                  <TableRow key={row.symbol}>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() =>
                          setOpenRow(isOpen ? null : row.symbol)
                        }
                      >
                        <ExpandMoreIcon />
                      </IconButton>
                    </TableCell>

                    {/* <TableCell>{row.symbol}</TableCell> */}
                    <TableCell
                            sx={{ cursor: "pointer", fontWeight: 500, color: "primary.main" }}
                            onClick={() =>
                              setOpenRow(openRow === row.symbol ? null : row.symbol)
                            }
                          >
                            {row.symbol}
                          </TableCell>

                    <TableCell>{row.score}</TableCell>
                    <TableCell>
                      <Chip label={advice.label} color={advice.color} />
                    </TableCell>
                  </TableRow>

                  <TableRow>
                    <TableCell colSpan={4} sx={{ p: 0 }}>
                      <Collapse in={isOpen} timeout="auto" unmountOnExit>
                            <Box sx={{ p: 2, bgcolor: "#fafafa" }}>
                                <Typography variant="subtitle1" fontWeight={600}>
                                  {row.symbol} — Medium-term Analysis
                                </Typography>

                                <Typography sx={{ mt: 1 }}>
                                  <b>Score:</b> {row.score}
                                </Typography>

                                <Typography sx={{ mt: 0.5 }}>
                                  <b>Advice:</b> {getAdvice(row.score).label}
                                </Typography>
                                {/* Box Insert  */}
                                <Box sx={{ mt: 1 }}>
                                    <Typography variant="body2">
                                      <b>Trend:</b> {breakdown.trend}
                                    </Typography>
                                    <Typography variant="body2">
                                      <b>Momentum:</b> {breakdown.momentum}
                                    </Typography>
                                    <Typography variant="body2">
                                      <b>Risk:</b> {breakdown.risk}
                                    </Typography>
                                  </Box>
                                {/* Box Insert  */}

                                <Typography sx={{ mt: 1 }} variant="body2">
                                  {row.explanation}
                                </Typography>
                              </Box>
                      </Collapse>
                    </TableCell>
                  </TableRow>
                </>
              )
            })}

            {filteredAndSortedStocks.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  No stocks match the selected score
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  )
}

export default StockTable
