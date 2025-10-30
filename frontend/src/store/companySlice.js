import { createSlice } from '@reduxjs/toolkit';

const companySlice = createSlice({
    name: 'company',
    initialState: {
        companies: [],
        activeCompany: null,
    },
    reducers: {
        setCompanies: (state, action) => {
            state.companies = action.payload;
        },
        setActiveCompany: (state, action) => {
            state.activeCompany = state.companies.find(c => c.id === action.payload);
        },
    },
});

export const { setCompanies, setActiveCompany } = companySlice.actions;
export default companySlice.reducer;
