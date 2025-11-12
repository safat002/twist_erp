import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  TextField,
  MenuItem,
  Button,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Stepper,
  Step,
  StepLabel,
  CircularProgress,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip
} from '@mui/material';
import {
  Add,
  Delete,
  Preview,
  Save,
  ExpandMore,
  Info,
  CheckCircle,
  Warning
} from '@mui/icons-material';
import landedCostService from '../../../services/landedCost';
import goodsReceiptService from '../../../services/goodsReceipt';

const EnhancedLandedCostForm = ({ grnId, onSuccess, onCancel }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [grn, setGRN] = useState(null);
  const [components, setComponents] = useState([
    {
      component_type: 'FREIGHT',
      description: '',
      total_amount: '',
      currency: 'USD',
      invoice_number: '',
      invoice_date: null,
      supplier_id: null
    }
  ]);
  const [apportionmentMethod, setApportionmentMethod] = useState('QUANTITY');
  const [notes, setNotes] = useState('');
  const [previewData, setPreviewData] = useState(null);
  const [errors, setErrors] = useState([]);

  const steps = ['Component Details', 'Preview Apportionment', 'Confirm & Apply'];

  useEffect(() => {
    if (grnId) {
      loadGRN();
    }
  }, [grnId]);

  const loadGRN = async () => {
    setLoading(true);
    try {
      const data = await goodsReceiptService.getGoodsReceipt(grnId);
      setGRN(data);
    } catch (error) {
      console.error('Error loading GRN:', error);
      alert('Failed to load GRN details');
    } finally {
      setLoading(false);
    }
  };

  const addComponent = () => {
    setComponents([
      ...components,
      {
        component_type: 'FREIGHT',
        description: '',
        total_amount: '',
        currency: 'USD',
        invoice_number: '',
        invoice_date: null,
        supplier_id: null
      }
    ]);
  };

  const removeComponent = (index) => {
    if (components.length > 1) {
      setComponents(components.filter((_, i) => i !== index));
    }
  };

  const updateComponent = (index, field, value) => {
    const updated = [...components];
    updated[index][field] = value;
    setComponents(updated);
  };

  const validateComponents = () => {
    const validationErrors = landedCostService.validateComponents(components);
    setErrors(validationErrors);
    return validationErrors.length === 0;
  };

  const handlePreview = async () => {
    if (!validateComponents()) return;

    setLoading(true);
    try {
      const preview = await landedCostService.previewApportionment(
        grnId,
        components,
        apportionmentMethod
      );
      setPreviewData(preview);
      setActiveStep(1);
    } catch (error) {
      console.error('Error previewing apportionment:', error);
      alert('Failed to preview apportionment: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    setLoading(true);
    try {
      await landedCostService.applyLandedCosts(
        grnId,
        components,
        apportionmentMethod,
        notes
      );
      alert('Landed costs applied successfully!');
      if (onSuccess) onSuccess();
    } catch (error) {
      console.error('Error applying landed costs:', error);
      alert('Failed to apply landed costs: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const renderComponentForm = () => (
    <Box>
      {errors.length > 0 && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Please fix the following errors:
          </Typography>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {errors.map((error, index) => (
              <li key={index}>{error}</li>
            ))}
          </ul>
        </Alert>
      )}

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            GRN Information
          </Typography>
          {grn && (
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  GRN Number: <strong>{grn.grn_number}</strong>
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Receipt Date: <strong>{grn.receipt_date}</strong>
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Warehouse: <strong>{grn.warehouse_name}</strong>
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Total Lines: <strong>{grn.lines?.length || 0}</strong>
                </Typography>
              </Grid>
            </Grid>
          )}
        </CardContent>
      </Card>

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Cost Components
            </Typography>
            <Button
              startIcon={<Add />}
              onClick={addComponent}
              variant="outlined"
              size="small"
            >
              Add Component
            </Button>
          </Box>

          {components.map((component, index) => (
            <Card key={index} variant="outlined" sx={{ mb: 2, p: 2 }}>
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} md={3}>
                  <TextField
                    select
                    fullWidth
                    size="small"
                    label="Component Type"
                    value={component.component_type}
                    onChange={(e) => updateComponent(index, 'component_type', e.target.value)}
                  >
                    {landedCostService.getComponentTypeOptions().map((option) => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid item xs={12} md={3}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Description"
                    value={component.description}
                    onChange={(e) => updateComponent(index, 'description', e.target.value)}
                  />
                </Grid>
                <Grid item xs={12} md={2}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Amount"
                    type="number"
                    value={component.total_amount}
                    onChange={(e) => updateComponent(index, 'total_amount', e.target.value)}
                    InputProps={{
                      startAdornment: <Typography sx={{ mr: 1 }}>$</Typography>
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={2}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Invoice #"
                    value={component.invoice_number}
                    onChange={(e) => updateComponent(index, 'invoice_number', e.target.value)}
                  />
                </Grid>
                <Grid item xs={12} md={1}>
                  <IconButton
                    color="error"
                    onClick={() => removeComponent(index)}
                    disabled={components.length === 1}
                  >
                    <Delete />
                  </IconButton>
                </Grid>
              </Grid>
            </Card>
          ))}

          <Divider sx={{ my: 3 }} />

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                select
                fullWidth
                label="Apportionment Method"
                value={apportionmentMethod}
                onChange={(e) => setApportionmentMethod(e.target.value)}
                helperText="How to distribute costs across GRN lines"
              >
                {landedCostService.getApportionmentMethodOptions().map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box display="flex" alignItems="center" height="100%">
                <Typography variant="body2" color="text.secondary">
                  Total Landed Cost: <strong>${landedCostService.calculateTotalLandedCost(components).toFixed(2)}</strong>
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Box display="flex" justifyContent="flex-end" gap={2}>
        {onCancel && (
          <Button onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button
          variant="contained"
          startIcon={<Preview />}
          onClick={handlePreview}
          disabled={loading}
        >
          {loading ? <CircularProgress size={24} /> : 'Preview Apportionment'}
        </Button>
      </Box>
    </Box>
  );

  const renderPreview = () => {
    if (!previewData) return null;

    const summary = landedCostService.generatePreviewSummary(previewData);

    return (
      <Box>
        {/* Summary Cards */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">
                  Total Landed Cost
                </Typography>
                <Typography variant="h5" color="primary">
                  ${summary.total_landed_cost.toFixed(2)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">
                  To Inventory
                </Typography>
                <Typography variant="h5" color="success.main">
                  ${summary.total_to_inventory.toFixed(2)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">
                  To COGS
                </Typography>
                <Typography variant="h5" color="warning.main">
                  ${summary.total_to_cogs.toFixed(2)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">
                  Affected Lines
                </Typography>
                <Typography variant="h5">
                  {summary.total_lines}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Line Details */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Line-by-Line Apportionment
            </Typography>

            {previewData.lines.map((line, index) => (
              <Accordion key={index} defaultExpanded={index === 0}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box display="flex" alignItems="center" justifyContent="space-between" width="100%">
                    <Typography fontWeight="medium">
                      {line.product_code} - {line.product_name}
                    </Typography>
                    <Chip
                      label={`Cost Adjustment: +$${line.total_cost_adjustment.toFixed(4)}/unit`}
                      color="primary"
                      size="small"
                      sx={{ mr: 2 }}
                    />
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={2} sx={{ mb: 2 }}>
                    <Grid item xs={3}>
                      <Typography variant="body2" color="text.secondary">
                        Quantity: <strong>{line.quantity}</strong>
                      </Typography>
                    </Grid>
                    <Grid item xs={3}>
                      <Typography variant="body2" color="text.secondary">
                        Original Cost: <strong>${line.original_unit_cost.toFixed(4)}</strong>
                      </Typography>
                    </Grid>
                    <Grid item xs={3}>
                      <Typography variant="body2" color="text.secondary">
                        New Cost: <strong>${line.new_unit_cost.toFixed(4)}</strong>
                      </Typography>
                    </Grid>
                    <Grid item xs={3}>
                      <Typography variant="body2" color="text.secondary">
                        Allocation: <strong>{line.allocation_percentage.toFixed(2)}%</strong>
                      </Typography>
                    </Grid>
                  </Grid>

                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Component</TableCell>
                          <TableCell align="right">Total Amount</TableCell>
                          <TableCell align="right">Apportioned</TableCell>
                          <TableCell align="right">To Inventory</TableCell>
                          <TableCell align="right">To COGS</TableCell>
                          <TableCell align="right">Per Unit</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {line.component_apportionments.map((comp, compIndex) => (
                          <TableRow key={compIndex}>
                            <TableCell>{comp.component_type_display}</TableCell>
                            <TableCell align="right">${comp.total_component_amount.toFixed(2)}</TableCell>
                            <TableCell align="right">${comp.apportioned_amount.toFixed(2)}</TableCell>
                            <TableCell align="right">${comp.to_inventory.toFixed(2)}</TableCell>
                            <TableCell align="right">${comp.to_cogs.toFixed(2)}</TableCell>
                            <TableCell align="right">${comp.cost_per_unit_adjustment.toFixed(4)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </AccordionDetails>
              </Accordion>
            ))}
          </CardContent>
        </Card>

        <Box display="flex" justifyContent="space-between" mt={3}>
          <Button onClick={() => setActiveStep(0)}>
            Back to Edit
          </Button>
          <Button
            variant="contained"
            onClick={() => setActiveStep(2)}
          >
            Continue to Confirm
          </Button>
        </Box>
      </Box>
    );
  };

  const renderConfirm = () => (
    <Box>
      <Alert severity="warning" sx={{ mb: 3 }}>
        <Typography variant="subtitle2" gutterBottom>
          Ready to Apply Landed Costs
        </Typography>
        <Typography variant="body2">
          This will update cost layers and post journal entries to the general ledger.
          This action cannot be undone.
        </Typography>
      </Alert>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Summary
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Typography variant="body2" color="text.secondary">
                GRN: <strong>{grn?.grn_number}</strong>
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body2" color="text.secondary">
                Components: <strong>{components.length}</strong>
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body2" color="text.secondary">
                Total Landed Cost: <strong>${landedCostService.calculateTotalLandedCost(components).toFixed(2)}</strong>
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body2" color="text.secondary">
                Method: <strong>{landedCostService.APPORTIONMENT_METHODS[apportionmentMethod]}</strong>
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <TextField
        fullWidth
        multiline
        rows={3}
        label="Notes (Optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        sx={{ mb: 3 }}
      />

      <Box display="flex" justifyContent="space-between">
        <Button onClick={() => setActiveStep(1)}>
          Back to Preview
        </Button>
        <Button
          variant="contained"
          color="primary"
          startIcon={<Save />}
          onClick={handleApply}
          disabled={loading}
        >
          {loading ? <CircularProgress size={24} /> : 'Apply Landed Costs'}
        </Button>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto', p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Enhanced Landed Cost Application
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Add and apportion landed costs to GRN #{grn?.grn_number}
      </Typography>

      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {activeStep === 0 && renderComponentForm()}
      {activeStep === 1 && renderPreview()}
      {activeStep === 2 && renderConfirm()}
    </Box>
  );
};

export default EnhancedLandedCostForm;
