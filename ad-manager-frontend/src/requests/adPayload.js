// Builds the body the ad manager expects for a new ad, from the ad form.
//
// Form fields hold text. The bid, budgets and priority are numbers in the API,
// so they are converted here, and a field left empty is left out.

// A datetime-local input gives the time as the user typed it, in their own
// timezone. The ad server reads flight dates as UTC with no offset, so the time
// is converted to UTC and written without the offset or milliseconds.
export function toUtcDateTime(localValue) {
  if (!localValue) {
    return null;
  }
  return new Date(localValue).toISOString().slice(0, 19);
}

function numberOrUndefined(text) {
  return text === '' || text === null || text === undefined ? undefined : Number(text);
}

function withoutUndefined(object) {
  return Object.fromEntries(Object.entries(object).filter(([, value]) => value !== undefined));
}

export function buildAdPayload(form, campaignId, advertiserId) {
  const payload = withoutUndefined({
    adname: form.adName,
    adpriority: numberOrUndefined(form.adPriority),
    adtype: form.adType,
    campaignid: campaignId,
    advertiserid: advertiserId,
    creativeid: form.creativeId,
    startdate: toUtcDateTime(form.startDate),
    enddate: toUtcDateTime(form.endDate),
    landingurl: form.landingUrl,
    // No ad unit picked means the ad may serve in any ad unit.
    ad_unit_targeted: form.adUnit ? [form.adUnit] : [],
  });

  const bidinfo = withoutUndefined({
    bidType: form.bidType || undefined,
    bid: numberOrUndefined(form.bid),
  });
  if (Object.keys(bidinfo).length > 0) {
    payload.bidinfo = bidinfo;
  }

  const budget = withoutUndefined({
    dailyBudget: numberOrUndefined(form.dailyBudget),
    totalBudget: numberOrUndefined(form.totalBudget),
  });
  if (Object.keys(budget).length > 0) {
    payload.budget = { currencyCode: 'USD', ...budget };
  }

  const targetinginfo = {};
  if (form.hours.length > 0) {
    targetinginfo.timeTargeting = { type: 'equal', values: form.hours };
  }
  if (form.days.length > 0) {
    targetinginfo.dayTargeting = { type: 'equal', values: form.days };
  }
  if (Object.keys(targetinginfo).length > 0) {
    payload.targetinginfo = targetinginfo;
  }

  return payload;
}
