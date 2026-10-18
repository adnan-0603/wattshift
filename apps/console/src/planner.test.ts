import {test} from 'node:test';import assert from 'node:assert/strict';import {schedule} from './planner.ts';
const t=Date.parse('2024-01-01T00:00:00Z');
const rows=[100,100,10,10].map((price,i)=>({start:new Date(t+i*3600000).toISOString(),end:new Date(t+(i+1)*3600000).toISOString(),price,carbon:null}));
test('cost units, optimal window and no invented carbon',()=>{const r=schedule(rows,t,t+4*3600000,2,1,900,1)!;assert.equal(r.baseline.cost,.2);assert.equal(r.best.cost,.02);assert.equal(r.carbonSaving,null);});
test('cannot cross data gap',()=>assert.equal(schedule([rows[0],rows[2]],t,t+4*3600000,2),null));
test('deadline infeasible',()=>assert.equal(schedule(rows,t,t+3600000,2),null));
test('overlap rejected',()=>assert.throws(()=>schedule([...rows,rows[0]],t,t+4*3600000,2)));
test('carbon requires coverage',()=>assert.equal(schedule(rows,t,t+4*3600000,2,4,300,1.2,0,'carbon'),null));
