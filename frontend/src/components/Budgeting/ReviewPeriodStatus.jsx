import React from 'react';
import { Tag, Tooltip } from 'antd';
import dayjs from 'dayjs';

const ReviewPeriodStatus = ({
  entryEndDate,
  gracePeriodDays,
  reviewStartDate,
  reviewEndDate,
  reviewEnabled,
  status,
}) => {
  const now = dayjs();
  const end = entryEndDate ? dayjs(entryEndDate) : null;
  const startReview = reviewStartDate ? dayjs(reviewStartDate) : (end && typeof gracePeriodDays === 'number' ? end.add(gracePeriodDays, 'day') : null);
  const endReview = reviewEndDate ? dayjs(reviewEndDate) : null;

  // Determine state
  // If reviewEnabled and dates include now => Review Open
  if (reviewEnabled && startReview && endReview && now.isAfter(startReview.subtract(1, 'day')) && now.isBefore(endReview.add(1, 'day'))) {
    const daysLeft = Math.max(endReview.diff(now, 'day'), 0);
    return <Tag color="blue">Review Open · {daysLeft}d left</Tag>;
  }

  // If entry closed and grace applies
  if ((status === 'ENTRY_CLOSED_REVIEW_PENDING' || status === 'ENTRY_OPEN' || status === 'DRAFT') && end && typeof gracePeriodDays === 'number') {
    if (startReview && now.isBefore(startReview)) {
      const days = Math.max(startReview.diff(now, 'day'), 0);
      return (
        <Tooltip title={`Review starts ${startReview.format('YYYY-MM-DD')}`}>
          <Tag color="gold">Grace Period · {days}d</Tag>
        </Tooltip>
      );
    }
  }

  if (reviewEnabled && startReview && endReview && now.isAfter(endReview)) {
    return <Tag>Review Closed</Tag>;
  }

  if (reviewEnabled) {
    return <Tag color="default">Review Pending</Tag>;
  }

  return <Tag color="default">No Review Window</Tag>;
};

export default ReviewPeriodStatus;

