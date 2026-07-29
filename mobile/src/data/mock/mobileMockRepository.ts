import type { MobileRepository } from '@/data/mobileRepository';
import { ALERT_FIXTURES, ASSET_FIXTURES, HOME_FIXTURE } from '@/data/mock/fixtures';

export const mobileMockRepository: MobileRepository = {
  async getHomeSummary() {
    return HOME_FIXTURE;
  },
  async listAssets() {
    return ASSET_FIXTURES;
  },
  async getAsset(assetId) {
    return ASSET_FIXTURES.find((asset) => asset.id === assetId) ?? null;
  },
  async listAlerts() {
    return ALERT_FIXTURES;
  },
  async getAlert(alertId) {
    return ALERT_FIXTURES.find((alert) => alert.id === alertId) ?? null;
  },
};
