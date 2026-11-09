import { buildAdPayload, toUtcDateTime } from './adPayload';

const emptyForm = {
  adName: 'Spring sale',
  adPriority: '',
  adType: 'NON_GUARANTEED',
  creativeId: 'CR1',
  startDate: '2026-11-08T10:00',
  endDate: '2026-11-09T10:00',
  landingUrl: 'https://example.com',
  adUnit: '',
  bidType: '',
  bid: '',
  dailyBudget: '',
  totalBudget: '',
  hours: [],
  days: [],
};

describe('toUtcDateTime', () => {
  test('writes the same moment in UTC, without an offset or milliseconds', () => {
    const utc = toUtcDateTime('2026-11-08T10:00');
    expect(utc).toMatch(/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$/);
    // The input has no offset, so it is local time. Read the output back as UTC: it must be the same moment.
    expect(new Date(`${utc}Z`).getTime()).toBe(new Date('2026-11-08T10:00').getTime());
  });

  test('an empty field stays empty', () => {
    expect(toUtcDateTime('')).toBeNull();
  });
});

describe('buildAdPayload', () => {
  test('sends the bid, budgets and priority as numbers', () => {
    const payload = buildAdPayload(
      { ...emptyForm, adPriority: '3', bidType: 'CPC', bid: '2.5', dailyBudget: '10', totalBudget: '100' },
      'C1',
      'A1',
    );
    expect(payload.adpriority).toBe(3);
    expect(payload.bidinfo).toEqual({ bidType: 'CPC', bid: 2.5 });
    expect(payload.budget).toEqual({ currencyCode: 'USD', dailyBudget: 10, totalBudget: 100 });
  });

  test('leaves out what was not filled in', () => {
    const payload = buildAdPayload(emptyForm, 'C1', 'A1');
    expect(payload).not.toHaveProperty('adpriority');
    expect(payload).not.toHaveProperty('bidinfo');
    expect(payload).not.toHaveProperty('budget');
    expect(payload).not.toHaveProperty('targetinginfo');
  });

  test('a budget with only a daily amount has only that amount', () => {
    const payload = buildAdPayload({ ...emptyForm, dailyBudget: '5' }, 'C1', 'A1');
    expect(payload.budget).toEqual({ currencyCode: 'USD', dailyBudget: 5 });
  });

  test('no ad unit picked is an empty list, not a list holding an empty list', () => {
    expect(buildAdPayload(emptyForm, 'C1', 'A1').ad_unit_targeted).toEqual([]);
    expect(buildAdPayload({ ...emptyForm, adUnit: 'ADU1' }, 'C1', 'A1').ad_unit_targeted).toEqual(['ADU1']);
  });

  test('targeting uses the key names the ad server reads, with hours 0 to 23', () => {
    const payload = buildAdPayload({ ...emptyForm, hours: [0, 23], days: [1, 7] }, 'C1', 'A1');
    expect(payload.targetinginfo).toEqual({
      timeTargeting: { type: 'equal', values: [0, 23] },
      dayTargeting: { type: 'equal', values: [1, 7] },
    });
  });

  test('carries the campaign and advertiser from the page', () => {
    const payload = buildAdPayload(emptyForm, 'C1', 'A1');
    expect(payload.campaignid).toBe('C1');
    expect(payload.advertiserid).toBe('A1');
  });
});
