import type {Snapshot,LiveJobs} from './types';
export const cluster=import.meta.env.VITE_MODE==='cluster';const api=import.meta.env.VITE_API_BASE||'/api';
export async function loadSnapshot():Promise<Snapshot>{const r=await fetch(cluster?`${api}/snapshot`:`${import.meta.env.BASE_URL}data/console.json`);if(!r.ok)throw Error(`Dataset unavailable (${r.status})`);const s=await r.json();if(s.schema_version!==1||!Array.isArray(s.prices))throw Error('Unsupported snapshot');return s;}
export async function loadJobs():Promise<LiveJobs>{if(!cluster)return{controller_connected:false,jobs:[]};const r=await fetch(`${api}/jobs`);if(!r.ok)throw Error('Controller unavailable');return r.json();}
