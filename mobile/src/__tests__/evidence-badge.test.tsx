import { render } from '@testing-library/react-native';

import { EvidenceBadge } from '@/components/EvidenceBadge';
import { EVIDENCE_CLASSES, EVIDENCE_LABELS } from '@/types/evidence';

describe('EvidenceBadge', () => {
  it.each(EVIDENCE_CLASSES)('renders the %s evidence class', (evidenceClass) => {
    const screen = render(<EvidenceBadge evidenceClass={evidenceClass} />);

    expect(
      screen.getByLabelText(`Clase de evidencia: ${EVIDENCE_LABELS[evidenceClass]}`),
    ).toBeTruthy();
    expect(screen.getByText(EVIDENCE_LABELS[evidenceClass])).toBeTruthy();
  });
});
