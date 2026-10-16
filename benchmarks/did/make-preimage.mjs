// Fixed public benchmark fixture; no production witness material.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as rt from '@midnight-ntwrk/compact-runtime';
import {Contract,ledger,pureCircuits} from './contract/index.js';
import {deriveJubjubPublicKeyFromSeed,signJubjubDigestFromSeed,TWO_248} from './signing.mjs';
const secret=new Uint8Array(32).fill(1),recovery=new Uint8Array(32).fill(2);
const witnesses={
 localControllerPublicKey:({privateState})=>[privateState,deriveJubjubPublicKeyFromSeed(secret)],
 localRecoveryAuthorityPublicKey:({privateState})=>[privateState,deriveJubjubPublicKeyFromSeed(recovery)],
 currentTimestamp:({privateState})=>[privateState,1700000000000n],
 getSchnorrReduction:({privateState},hash)=>[privateState,[hash/TWO_248,hash%TWO_248]],
};
const contract=new Contract(witnesses);
const init=contract.initialState(rt.createConstructorContext({secretKey:secret,recoverySecretKey:recovery},'0'.repeat(64)));
const ctx=rt.createCircuitContext(rt.sampleContractAddress(),init.currentZswapLocalState,init.currentContractState,init.currentPrivateState);
const before=ledger(ctx.currentQueryContext.state);
const digest=pureCircuits.deactivateAuthorizationDigest(before.id,before.version);
const signature=signJubjubDigestFromSeed(secret,digest);
assert.equal(before.active,true);
assert.equal(before.deactivated,false);
const result=contract.impureCircuits.deactivate(ctx,signature,before.version);
const after=ledger(result.context.currentQueryContext.state);
assert.equal(after.active,false);assert.equal(after.deactivated,true);assert.equal(after.version,before.version+1n);
const data=result.proofData;
const encoded=rt.proofDataIntoSerializedPreimage(data.input,data.output,data.publicTranscript,data.privateTranscriptOutputs,'deactivate');
fs.writeFileSync('preimage.bin',encoded);
console.log(JSON.stringify({assertions:5,preimageBytes:encoded.length,publicOps:data.publicTranscript.length,privateOutputs:data.privateTranscriptOutputs.length}));
