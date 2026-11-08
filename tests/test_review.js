const assert = require('node:assert/strict');
const {mergeManualCorrections} = require('../web/review.js');

let previous = {one:{score:0,status:'Ausente',manual_status:true,manual_score:true,origin:'ocr'}, two:{score:5,status:'Presente',origin:'ocr'}};
let fresh = {one:{score:100,status:'Presente',origin:'ocr'}, two:{score:0,status:'Ausente',origin:'ocr'}};
let result = mergeManualCorrections(previous, fresh);
assert.equal(result.one.score, 0);
assert.equal(result.one.status, 'Ausente');
assert.equal(result.two.status, 'Ausente');
assert.equal(mergeManualCorrections({one:previous.one}, {}).one.status, 'Ausente');
assert.equal(mergeManualCorrections({one:{score:0,status:'Ausente'}}, {one:{score:1,status:'Presente',origin:'ocr'}}).one.status, 'Ausente');
result = mergeManualCorrections({one:{score:0,status:'Ausente',manual_status:true,origin:'ocr'}}, {one:{score:100,status:'Presente',duplicate:true,origin:'ocr'}});
assert.equal(result.one.status, 'Ausente');
assert.equal(result.one.score, 100);
assert.equal(result.one.duplicate, true);
result = mergeManualCorrections({one:{score:0,status:'Ausente',manual_score:true,origin:'ocr'}}, {one:{score:50,status:'Revisar',origin:'ocr'}});
assert.equal(result.one.score, 0);
assert.equal(result.one.status, 'Revisar');
console.log('Preservação de correções: OK');
