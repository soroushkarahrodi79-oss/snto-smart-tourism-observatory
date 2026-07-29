import { TAB_DEFINITIONS } from '@/app/(tabs)/_layout';

describe('mobile navigation contract', () => {
  it('exposes exactly the five approved top-level tabs', () => {
    expect(TAB_DEFINITIONS).toEqual([
      { name: 'index', title: 'Inicio' },
      { name: 'map', title: 'Mapa' },
      { name: 'assets', title: 'Activos' },
      { name: 'alerts', title: 'Alertas' },
      { name: 'profile', title: 'Perfil' },
    ]);
  });
});
