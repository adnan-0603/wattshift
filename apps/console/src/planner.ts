import type {Interval} from './types.ts';
export type Window={start:string;end:string;cost:number;carbon:number|null;energy:number;avg:number};
export function schedule(rows:Interval[],release:number,deadline:number,hours:number,gpus=4,watts=300,pue=1.2,adder=0,objective='cost'){
 if(![release,deadline,hours,gpus,watts,pue,adder].every(Number.isFinite)||hours<=0||gpus<1||watts<=0||pue<1||deadline<=release)throw Error('Invalid job parameters');
 const data=[...rows].sort((a,b)=>Date.parse(a.start)-Date.parse(b.start));
 for(let i=0;i<data.length;i++){if(Date.parse(data[i].end)<=Date.parse(data[i].start)||!Number.isFinite(data[i].price))throw Error('Invalid interval');if(i&&Date.parse(data[i].start)<Date.parse(data[i-1].end))throw Error('Overlapping intervals');}
 const eligible=data.filter(r=>Date.parse(r.start)>=release&&Date.parse(r.end)<=deadline);const duration=hours*3600000;const kw=(gpus*watts+100)*pue/1000;const choices:Window[]=[];
 for(let i=0;i<eligible.length;i++){let cost=0,energy=0,co=0,carbonKnown=true,weighted=0;const begin=Date.parse(eligible[i].start);
  for(let j=i;j<eligible.length;j++){const r=eligible[j];if(j>i&&Date.parse(eligible[j-1].end)!==Date.parse(r.start))break;const elapsed=Date.parse(r.end)-begin;if(elapsed>duration)break;const h=(Date.parse(r.end)-Date.parse(r.start))/3600000;const e=kw*h;cost+=e*(r.price/1000+adder);energy+=e;weighted+=r.price*h;if(r.carbon===null)carbonKnown=false;else co+=e*r.carbon/1000;
   if(elapsed===duration){choices.push({start:eligible[i].start,end:r.end,cost,energy,carbon:carbonKnown?co:null,avg:weighted/hours});break;}
  }
 }
 if(!choices.length)return null;
 if(objective==='carbon'&&choices.some(c=>c.carbon===null))return null;
 const best=choices.reduce((a,b)=>(objective==='carbon'?b.carbon!<a.carbon!:b.cost<a.cost)?b:a);
 const baseline=choices[0];return {baseline,best,savings:baseline.cost-best.cost,percent:baseline.cost>0?100*(baseline.cost-best.cost)/baseline.cost:null,carbonSaving:baseline.carbon===null||best.carbon===null?null:baseline.carbon-best.carbon,windows:choices.length};
}
