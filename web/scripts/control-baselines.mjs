import baseline from '../src/data/canary-control-baseline.json' with { type: 'json' };
import m5 from '../src/data/methodology-control-baselines/m5.json' with { type: 'json' };

// Version additions live separately so the experiment's frozen JSON stays byte-identical.
export default { ...baseline, versions: { ...baseline.versions, m5 } };
