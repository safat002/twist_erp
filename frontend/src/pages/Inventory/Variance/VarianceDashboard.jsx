import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  TextField,
  MenuItem,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  Tooltip
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  CheckCircle,
  PendingActions,
  Visibility,
  PostAdd,
  FileDownload,
  Refresh
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, Legend, ResponsiveContainer } from 'recharts';
import varianceService from '../../../services/variance';

const VarianceDashboard = () => {
  const [tab, setTab] = useState(0); // 0 = Standard Cost, 1 = Purchase Price
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState(null);
  const [standardVariances, setStandardVariances] = useState([]);
  const [ppvVariances, setPPVVariances] = useState([]);
  const [filters, setFilters] = useState({
    start_date: null,
    end_date: null,
    product: '',
    warehouse: '',
    posted_to_gl: ''
  });
  const [selectedVariance, setSelectedVariance] = useState(null);
  const [detailDialog, setDetailDialog] = useState(false);
  const [postingDialog, setPostingDialog] = useState(false);

  useEffect(() => {
    loadData();
  }, [tab, filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load summary
      const summaryData = await varianceService.getVarianceSummary(filters);
      setSummary(summaryData);

      // Load variances based on active tab
      if (tab === 0) {
        const scvData = await varianceService.getStandardCostVariances(filters);
        setStandardVariances(scvData.results || []);
      } else {
        const ppvData = await varianceService.getPurchasePriceVariances(filters);
        setPPVVariances(ppvData.results || []);
      }
    } catch (error) {
      console.error('Error loading variance data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePostToGL = async () => {
    if (!selectedVariance) return;

    setLoading(true);
    try {
      if (tab === 0) {
        await varianceService.postStandardVarianceToGL(selectedVariance.id);
      } else {
        await varianceService.postPPVToGL(selectedVariance.id);
      }
      alert('Variance posted to GL successfully');
      setPostingDialog(false);
      setSelectedVariance(null);
      loadData();
    } catch (error) {
      console.error('Error posting to GL:', error);
      alert('Failed to post to GL: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const getSummaryCards = () => {
    if (!summary) return [];

    const type = tab === 0 ? 'standard_cost_variance' : 'purchase_price_variance';
    const data = summary[type] || {};

    return [
      {
        title: 'Favorable Variances',
        value: `$${data.favorable?.toFixed(2) || '0.00'}`,
        icon: <TrendingDown />,
        color: 'success',
        count: data.count || 0
      },
      {
        title: 'Unfavorable Variances',
        value: `$${data.unfavorable?.toFixed(2) || '0.00'}`,
        icon: <TrendingUp />,
        color: 'error',
        count: data.count || 0
      },
      {
        title: 'Net Variance',
        value: `$${data.net?.toFixed(2) || '0.00'}`,
        icon: data.net > 0 ? <TrendingUp /> : <TrendingDown />,
        color: data.net > 0 ? 'error' : 'success',
        count: data.count || 0
      },
      {
        title: 'Total Records',
        value: data.count || 0,
        icon: <CheckCircle />,
        color: 'primary',
        count: data.count || 0
      }
    ];
  };

  const getChartData = () => {
    const variances = tab === 0 ? standardVariances : ppvVariances;

    // Aggregate by variance type
    const favorable = variances
      .filter(v => v.variance_type === 'FAVORABLE')
      .reduce((sum, v) => sum + Math.abs(v.total_variance_amount), 0);

    const unfavorable = variances
      .filter(v => v.variance_type === 'UNFAVORABLE')
      .reduce((sum, v) => sum + v.total_variance_amount, 0);

    return [
      { name: 'Favorable', value: favorable, color: '#4caf50' },
      { name: 'Unfavorable', value: unfavorable, color: '#f44336' }
    ];
  };

  const renderSummaryCards = () => (
    <Grid container spacing={3} sx={{ mb: 3 }}>
      {getSummaryCards().map((card, index) => (
        <Grid item xs={12} sm={6} md={3} key={index}>
          <Card sx={{ height: '100%', bgcolor: `${card.color}.50` }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    {card.title}
                  </Typography>
                  <Typography variant="h5" sx={{ mt: 1, fontWeight: 'bold' }}>
                    {card.value}
                  </Typography>
                </Box>
                <Box sx={{ color: `${card.color}.main`, fontSize: 40 }}>
                  {card.icon}
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );

  const renderFilters = () => (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={3}>
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DatePicker
                label="Start Date"
                value={filters.start_date}
                onChange={(date) => setFilters({ ...filters, start_date: date })}
                renderInput={(params) => <TextField {...params} fullWidth size="small" />}
              />
            </LocalizationProvider>
          </Grid>
          <Grid item xs={12} md={3}>
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DatePicker
                label="End Date"
                value={filters.end_date}
                onChange={(date) => setFilters({ ...filters, end_date: date })}
                renderInput={(params) => <TextField {...params} fullWidth size="small" />}
              />
            </LocalizationProvider>
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField
              select
              fullWidth
              size="small"
              label="GL Posted"
              value={filters.posted_to_gl}
              onChange={(e) => setFilters({ ...filters, posted_to_gl: e.target.value })}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="true">Posted</MenuItem>
              <MenuItem value="false">Pending</MenuItem>
            </TextField>
          </Grid>
          <Grid item xs={12} md={2}>
            <Button
              fullWidth
              variant="contained"
              startIcon={<Refresh />}
              onClick={loadData}
            >
              Refresh
            </Button>
          </Grid>
          <Grid item xs={12} md={2}>
            <Button
              fullWidth
              variant="outlined"
              startIcon={<FileDownload />}
              onClick={() => alert('Export functionality coming soon')}
            >
              Export
            </Button>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  const renderCharts = () => {
    const chartData = getChartData();

    return (
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Variance Distribution
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <ChartTooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Favorable vs Unfavorable
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <ChartTooltip />
                  <Legend />
                  <Bar dataKey="value" fill="#8884d8">
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };

  const renderVarianceTable = () => {
    const variances = tab === 0 ? standardVariances : ppvVariances;

    return (
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              {tab === 0 ? 'Standard Cost Variances' : 'Purchase Price Variances'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {variances.length} records
            </Typography>
          </Box>

          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell>Product</TableCell>
                  <TableCell>Warehouse</TableCell>
                  {tab === 0 && <TableCell>Transaction Type</TableCell>}
                  {tab === 1 && <TableCell>GRN</TableCell>}
                  <TableCell align="right">Quantity</TableCell>
                  <TableCell align="right">Standard/PO</TableCell>
                  <TableCell align="right">Actual/Invoice</TableCell>
                  <TableCell align="right">Variance</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>GL Status</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={13} align="center">
                      <CircularProgress />
                    </TableCell>
                  </TableRow>
                ) : variances.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={13} align="center">
                      No variances found
                    </TableCell>
                  </TableRow>
                ) : (
                  variances.map((variance) => (
                    <TableRow key={variance.id} hover>
                      <TableCell>{variance.id}</TableCell>
                      <TableCell>
                        {tab === 0
                          ? variance.transaction_date
                          : variance.goods_receipt?.receipt_date || 'N/A'
                        }
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {variance.product_code}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {variance.product_name}
                        </Typography>
                      </TableCell>
                      <TableCell>{variance.warehouse_code}</TableCell>
                      {tab === 0 && (
                        <TableCell>{variance.transaction_type_display}</TableCell>
                      )}
                      {tab === 1 && (
                        <TableCell>{variance.grn_number}</TableCell>
                      )}
                      <TableCell align="right">{variance.quantity}</TableCell>
                      <TableCell align="right">
                        ${(tab === 0 ? variance.standard_cost : variance.po_price)?.toFixed(4)}
                      </TableCell>
                      <TableCell align="right">
                        ${(tab === 0 ? variance.actual_cost : variance.invoice_price)?.toFixed(4)}
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          fontWeight="bold"
                          color={variance.variance_type === 'FAVORABLE' ? 'success.main' : 'error.main'}
                        >
                          ${variance.total_variance_amount?.toFixed(2)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={variance.variance_type}
                          size="small"
                          color={variance.variance_type === 'FAVORABLE' ? 'success' : 'error'}
                          icon={variance.variance_type === 'FAVORABLE' ? <TrendingDown /> : <TrendingUp />}
                        />
                      </TableCell>
                      <TableCell>
                        {variance.posted_to_gl ? (
                          <Chip
                            label={`Posted (JE#${variance.variance_je_id})`}
                            size="small"
                            color="success"
                            icon={<CheckCircle />}
                          />
                        ) : (
                          <Chip
                            label="Pending"
                            size="small"
                            color="warning"
                            icon={<PendingActions />}
                          />
                        )}
                      </TableCell>
                      <TableCell>
                        <Tooltip title="View Details">
                          <IconButton
                            size="small"
                            onClick={() => {
                              setSelectedVariance(variance);
                              setDetailDialog(true);
                            }}
                          >
                            <Visibility />
                          </IconButton>
                        </Tooltip>
                        {!variance.posted_to_gl && (
                          <Tooltip title="Post to GL">
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={() => {
                                setSelectedVariance(variance);
                                setPostingDialog(true);
                              }}
                            >
                              <PostAdd />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Variance Reports Dashboard
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Track and analyze standard cost and purchase price variances
      </Typography>

      {renderSummaryCards()}
      {renderFilters()}
      {renderCharts()}

      <Tabs
        value={tab}
        onChange={(e, newValue) => setTab(newValue)}
        sx={{ mb: 2 }}
      >
        <Tab label="Standard Cost Variance" />
        <Tab label="Purchase Price Variance" />
      </Tabs>

      {renderVarianceTable()}

      {/* Posting Confirmation Dialog */}
      <Dialog open={postingDialog} onClose={() => setPostingDialog(false)}>
        <DialogTitle>Post Variance to GL</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This will create a journal entry and post the variance to the general ledger.
            This action cannot be undone.
          </Alert>
          <Typography variant="body2" paragraph>
            <strong>Variance Amount:</strong> ${selectedVariance?.total_variance_amount?.toFixed(2)}
          </Typography>
          <Typography variant="body2" paragraph>
            <strong>Type:</strong> {selectedVariance?.variance_type}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPostingDialog(false)}>Cancel</Button>
          <Button
            variant="contained"
            color="primary"
            onClick={handlePostToGL}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Post to GL'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default VarianceDashboard;
