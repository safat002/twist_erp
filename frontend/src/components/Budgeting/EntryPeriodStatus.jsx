import React from 'react';
import { Tag } from 'antd';
import dayjs from 'dayjs';

const EntryPeriodStatus = ({ entryStartDate, entryEndDate, status }) => {
  const now = dayjs();
  const end = entryEndDate ? dayjs(entryEndDate) : null;

  let color = 'default';
  let text = 'No Entry Window';

  if (status === 'ENTRY_OPEN') {
    color = 'green';
    text = 'Entry Open';
    if (end) {
      const days = end.diff(now, 'day');
      text = `Entry Open · ${days >= 0 ? days : 0}d left`;
      if (days <= 1) color = 'orange';
    }
  }

  return <Tag color={color}>{text}</Tag>;
};

export default EntryPeriodStatus;

