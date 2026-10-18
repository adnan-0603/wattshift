// @vitest-environment jsdom
import React from 'react';
import {afterEach,describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,cleanup,waitFor} from '@testing-library/react';
import fs from 'node:fs';
vi.mock('./Chart',()=>({default:({label}:{label:string})=><div role="img" aria-label={label}/> }));
vi.mock('./data',()=>({cluster:false,loadSnapshot:async()=>JSON.parse(fs.readFileSync(process.cwd()+'/public/data/console.json','utf8')),loadJobs:async()=>({controller_connected:false,jobs:[]})}));
import {App} from './main';
afterEach(cleanup);
describe('Console workflows (DOM tests; not visual browser QA)',()=>{
 it('loads actual snapshot, visits all pages and updates calculator',async()=>{
  render(<App/>);await screen.findByText('A better time to compute.');
  fireEvent.click(screen.getByRole('button',{name:/Forecast/}));await screen.findByText('See the hours ahead.');
  fireEvent.click(screen.getByRole('button',{name:/Jobs/}));await screen.findByText('Every workload has a window.');
  fireEvent.click(screen.getByRole('button',{name:/Savings/}));await screen.findByText('The difference timing makes.');
  fireEvent.click(screen.getByRole('button',{name:/Calculator/}));await screen.findByText('What could your run save?');
  const slider=screen.getByRole('slider',{name:/GPU count/});fireEvent.change(slider,{target:{value:'8'}});
  await waitFor(()=>expect(screen.getByText('8 GPUs')).toBeTruthy());
  fireEvent.change(screen.getByLabelText('Season'),{target:{value:'Winter'}});expect(screen.getByDisplayValue('Winter')).toBeTruthy();
 });
});
