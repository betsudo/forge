// Run from owned scratch with exact pinned dependencies; no consumer source edits.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import * as rt from '@midnight-ntwrk/compact-runtime';
const {Contract,ledger,pureCircuits} = await import(pathToFileURL(process.argv[2]).href);
const circuit=process.argv[4]??'deposit_unshielded';
assert.ok(['deposit_unshielded','activate_initial_device_with_jubjub'].includes(circuit));
let witnessCalls=0;
const contract = new Contract({held_coin:()=>{witnessCalls++;throw new Error('selected circuits must not request a shielded coin witness');}});
const zero = new Uint8Array(32), salt=new Uint8Array(32).fill(7);
const recovery = rt.ecMulGenerator(1n);
const boot=circuit==='deposit_unshielded'?zero:await pureCircuits.derive_boot_commitment_with_jubjub(salt,recovery);
const init = await contract.initialState(rt.createConstructorContext({},'0'.repeat(64)),boot,zero,recovery,new Uint8Array(64),60n);
const ctx = rt.createCircuitContext({circuitId:circuit,contractAddress:"1".repeat(64),coinPublicKeyOrZswapState:init.currentZswapLocalState,contractState:init.currentContractState,privateState:init.currentPrivateState,time:1700000000000});
const before=ledger(ctx.callContext.currentQueryContext.state);
assert.equal(before.round,0n);
assert.equal(before.auth_nonce,0n);
let result, assertions=2;
if(circuit==='deposit_unshielded') {
 assert.equal(before.unshielded_balances.member(zero),false);
 result=await contract.impureCircuits.deposit_unshielded(ctx,zero,10000n);
 const after=ledger(result.context.callContext.currentQueryContext.state);
 assert.equal(after.unshielded_balances.member(zero),true);
 assert.equal(after.unshielded_balances.lookup(zero),10000n);
 assert.equal(after.round,1n);
 assert.equal(after.auth_nonce,before.auth_nonce);
 assertions+=5;
} else {
 assert.equal(before.booted,false);
 result=await contract.impureCircuits.activate_initial_device_with_jubjub(ctx,recovery,salt);
 const after=ledger(result.context.callContext.currentQueryContext.state);
 assert.equal(after.booted,true);
 assert.equal(after.device_count,1n);
 assert.equal(after.round,1n);
 assert.equal(after.auth_nonce,before.auth_nonce);
 assertions+=5;
}
assert.equal(witnessCalls,0);
assert.equal(result.context.callProofDataTrace.length,1);
assertions+=2;
const data=result.context.callProofDataTrace[0];
const encoded=rt.proofDataIntoSerializedPreimage(data.input,data.output,data.publicTranscript,data.privateTranscriptOutputs,circuit);
fs.writeFileSync(process.argv[3],encoded);
console.log(JSON.stringify({circuit,assertions,preimageBytes:encoded.length,privateWitnessCalls:witnessCalls,publicOps:data.publicTranscript.length,privateOutputs:data.privateTranscriptOutputs.length}));
