import {expect,test} from 'vitest';
import {score,Match} from './api';
test('missing scores are not fabricated',()=>{expect(score({home_score:null,away_score:null} as Match)).toBe('—');expect(score({home_score:0,away_score:0} as Match)).toBe('0 : 0');});
