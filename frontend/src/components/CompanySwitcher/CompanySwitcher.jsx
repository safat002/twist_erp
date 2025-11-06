import React, { useState, useEffect } from 'react';
import { Select } from 'antd';
import { useDispatch, useSelector } from 'react-redux';
import { setActiveCompany } from '../../store/companySlice';
import api from '../../services/api';

const CompanySwitcher = () => {
    const dispatch = useDispatch();
    const { companies, activeCompany } = useSelector(state => state.company);
    const [loading, setLoading] = useState(false);

    const handleCompanyChange = async (companyId) => {
        setLoading(true);
        try {
            await api.post('/companies/switch/', { company_id: companyId });
            dispatch(setActiveCompany(companyId));
            // Avoid full page reload; state update is enough
        } catch (error) {
            console.error('Failed to switch company:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Select
            value={activeCompany?.id}
            onChange={handleCompanyChange}
            loading={loading}
            style={{ width: 200 }}
            placeholder="Select Company"
        >
            {companies.map(company => (
                <Select.Option key={company.id} value={company.id}>
                    {company.code} - {company.name}
                </Select.Option>
            ))}
        </Select>
    );
};

export default CompanySwitcher;
