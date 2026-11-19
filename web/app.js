'use strict';
const $=s=>document.querySelector(s), esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=v=>Number(v||0).toLocaleString('ko-KR')+'원';
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
const labels={ACTIVE:'수강 중',INACTIVE:'비활성',BLACK:'블랙리스트',COMPLETED:'수료',CANCELED:'취소',PAID:'완납',UNPAID:'미납',REFUNDED:'환불'};
const badge=(v,student=false)=>`<span class="badge ${v==='ACTIVE'?'active':v==='BLACK'?'black':''}">${esc(student&&v==='ACTIVE'?'활성':labels[v]||v)}</span>`;
let state={},page='dashboard',generation=0;
const routes={dashboard:['운영 현황','학원의 주요 현황과 최근 업무를 한눈에 확인하세요.'],students:['학생 관리','학생 정보와 재원 상태, 수강 내역을 관리합니다.','학생 등록'],teachers:['선생님 관리','선생님 정보를 관리하고 담당 반을 확인합니다.','선생님 등록'],courses:['수강 과정','과정별 수강비를 설정하고 관리합니다.','과정 등록'],classes:['반 관리','정규반·특강과 담당 선생님, 주간 시간표를 관리합니다.','반 개설'],enrollments:['수강 관리','학생의 반 배정과 수강 상태를 관리합니다.','수강 등록'],payments:['결제 관리','수강료를 등록하고 학생별·기간별 수납 내역을 확인합니다.','결제 등록']};
const paths={dashboard:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',students:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M20 8v6 M17 11h6',teachers:'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M4 21v-2a6 6 0 0 1 6-5h4a6 6 0 0 1 6 5v2',courses:'M4 3h6a3 3 0 0 1 3 3v15a4 4 0 0 0-4-3H4z M13 6a3 3 0 0 1 3-3h5v15h-4a4 4 0 0 0-4 3',classes:'M3 21h18 M5 21V4h14v17 M9 8h1 M14 8h1 M9 12h1 M14 12h1 M10 21v-5h4v5',enrollments:'M8 4H4v17h16V4h-4 M8 2h8v5H8z M8 12l2 2 5-5 M8 18h8',payments:'M3 5h18v14H3z M3 10h18 M7 15h3'};
$('#nav').innerHTML=Object.entries(routes).map(([k,v])=>`<a href="#${k}" data-nav="${k}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[k]}"/></svg>${v[0]}</a>`).join('');
$('#today').textContent=new Intl.DateTimeFormat('ko-KR',{year:'numeric',month:'long',day:'numeric',weekday:'short'}).format(new Date());
async function api(url,data){const r=await fetch(url,data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});const json=await r.json();if(!r.ok)throw Error(json.error||'요청을 처리하지 못했습니다.');return json}
function toast(message){$('#toast').textContent=message;$('#toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').hidden=true,3500)}
function table(headers,rows,empty='등록된 항목이 없습니다.'){return `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.join(''):`<tr><td colspan="${headers.length}" class="empty"><strong>${esc(empty)}</strong>조건을 바꾸거나 새로운 항목을 등록하세요.</td></tr>`}</tbody></table></div>`}
const tr=cells=>`<tr>${cells.map((v,i)=>`<td${i===1?' class="name"':''}>${v}</td>`).join('')}</tr>`;
const button=(text,action,id)=>`<button data-action="${action}" data-id="${id}">${text}</button>`;
const actions=items=>`<div class="row-actions">${items.join('')}</div>`;
const card=(title,sub,body)=>`<div class="card"><div class="card-head"><div><h2>${title}</h2><p>${sub}</p></div></div>${body}</div>`;
function studentRows(rows){return rows.map(r=>tr([`<span class="badge">${r.student_id}</span>`,esc(r.name),esc(r.school)||'—',esc(r.grade)||'—',esc(r.contact_number)||'—',badge(r.student_classification,true),actions([button('수강 내역','student.history',r.student_id),button('수정','student.edit',r.student_id)])]))}
function listing(){let rows,headers,title,count;
if(page==='students'){rows=studentRows(state.students);headers=['ID','학생명','학교','학년','연락처','상태','관리'];title='전체 학생';count=state.students.length}
if(page==='teachers'){rows=state.teachers.map(r=>tr([r.teacher_id,esc(r.name),esc(r.contact_number)||'—',esc(state.classes.filter(c=>c.teacher_id===r.teacher_id).map(c=>c.class_name).join(', '))||'미배정',button('수정','teacher.edit',r.teacher_id)]));headers=['ID','선생님','연락처','담당 반','관리'];title='선생님 목록';count=state.teachers.length}
if(page==='courses'){rows=state.courses.map(r=>tr([r.course_id,esc(r.name),money(r.fee),state.classes.filter(c=>c.course_id===r.course_id).length+'개',button('수정','course.edit',r.course_id)]));headers=['ID','과정명','수강비','개설 반','관리'];title='수강 과정 목록';count=state.courses.length}
if(page==='classes'){rows=state.classes.map(r=>tr([r.class_id,`${esc(r.class_name)}<small>${r.start_date?'특강':'정규반'}</small>`,esc(r.course_name),esc(r.teacher_name)||'미지정',esc(r.grade)||'—',r.start_date?`${esc(r.start_date)} ~ ${esc(r.end_date)}`:'—',actions([button('명단','class.roster',r.class_id),button('시간표','class.schedule',r.class_id),button('수정','class.edit',r.class_id)])]));headers=['ID','반 이름','수강 과정','담당 선생님','학년','특강 기간','관리'];title='개설 반 목록';count=state.classes.length}
if(page==='enrollments'){rows=state.enrollments.map(r=>tr([r.enrollment_id,esc(r.student_name),esc(r.class_name),esc(r.enrolled_date),badge(r.status),button('상태 변경','enrollment.edit',r.enrollment_id)]));headers=['ID','학생명','반 이름','등록일','수강 상태','관리'];title='수강 등록 목록';count=state.enrollments.length}
return card(title,`총 ${count}건 · 목록에서 정보를 확인하고 관리하세요.`,`<div class="toolbar"><input type="search" class="search" id="search" placeholder="이름, 반, 과정 등으로 검색" aria-label="목록 검색"><span id="search-count">전체 ${count}건</span></div><div id="listing-table">${table(headers,rows)}</div><div class="card-bottom">등록된 정보는 저장 즉시 다른 메뉴에도 반영됩니다.</div>`)}
async function render(){const token=++generation;page=location.hash.slice(1);if(!routes[page])page='dashboard';$('#title').textContent=routes[page][0];$('#subtitle').textContent=routes[page][1];document.title=routes[page][0]+' · Academy';document.querySelectorAll('[data-nav]').forEach(a=>{a.classList.toggle('active',a.dataset.nav===page);a.setAttribute('aria-current',a.dataset.nav===page?'page':'false')});$('#primary').hidden=!routes[page][2];$('#primary').textContent='+ '+(routes[page][2]||'');$('#content').innerHTML='<div class="empty">데이터를 불러오는 중입니다…</div>';
try{state=await api('/api/state');if(token!==generation)return;if(page==='dashboard'){const pay=await api('/api/payments');if(token!==generation)return;dashboard(pay)}else if(page==='payments'){await payments(token)}else{$('#content').innerHTML=listing();$('#search').addEventListener('input',e=>{let count=0;document.querySelectorAll('#listing-table tbody tr').forEach(row=>{const match=row.textContent.toLowerCase().includes(e.target.value.toLowerCase());row.hidden=!match;if(match)count++});$('#search-count').textContent=`검색 결과 ${count}건`})}}catch(e){if(token===generation)$('#content').innerHTML=`<div class="error" role="alert">${esc(e.message)}</div><button data-action="retry">다시 시도</button>`}}
function dashboard(pay){const active=state.students.filter(s=>s.student_classification==='ACTIVE').length;const tiles=[['전체 학생',state.students.length,'명',`활성 학생 ${active}명`,'♙'],['운영 중인 반',state.classes.length,'개',`정규 ${state.classes.filter(c=>!c.start_date).length} · 특강 ${state.classes.filter(c=>c.start_date).length}`,'▦'],['수강 중인 등록',state.enrollments.filter(e=>e.status==='ACTIVE').length,'건','현재 ACTIVE 수강 기준','≡'],['누적 수납',Number(pay.total).toLocaleString('ko-KR'),'원',`전체 결제 ${pay.rows.length}건`,'₩']];
$('#content').innerHTML=`<div class="stats">${tiles.map(t=>`<div class="stat"><div class="stat-top">${t[0]}<span class="stat-symbol">${t[4]}</span></div><strong>${t[1]}<small>${t[2]}</small></strong><p>${t[3]}</p></div>`).join('')}</div><div class="grid-two">${card('최근 등록 학생','최근 등록된 학생 5명을 확인하세요.',table(['ID','학생명','학교','상태'],state.students.slice(-5).reverse().map(s=>tr([s.student_id,esc(s.name),esc(s.school)||'—',badge(s.student_classification,true)]))))}${card('최근 결제 내역','결제일 기준 최근 수납 내역입니다.',table(['학생명','수강 과정','금액','결제일'],pay.rows.filter(r=>r.status==='PAID').slice(0,5).map(r=>tr([esc(r.student_name),esc(r.course_name),money(r.course_fee),esc(r.payment_date)]))))}</div><p class="section-label">자주 사용하는 업무</p><div class="quick-links"><a href="#students">학생 정보 관리 <span>↗</span></a><a href="#classes">반 · 시간표 관리 <span>↗</span></a><a href="#enrollments">수강 등록 및 상태 변경 <span>↗</span></a><a href="#payments">결제 등록 · 수납 조회 <span>↗</span></a></div>`;
}
const opts=(rows,idKey,nameKey,selected='',blank='선택하세요')=>`<option value="">${blank}</option>`+rows.map(r=>`<option value="${r[idKey]}" ${String(r[idKey])===String(selected)?'selected':''}>${esc(r[nameKey])} (ID: ${r[idKey]})</option>`).join('');
async function payments(token){
    const month = today().slice(0,7);
    const targets = card('결제 대상','청구월에 해당하는 현재 수강 건입니다.',
        `<form id="target-filter" class="toolbar">
            <label>대상 청구월 <input type="month" name="billing_month" value="${month}" required></label>
            <button class="primary">대상 조회</button>
        </form><div id="target-results"></div>`);
    const history = card('결제 내역','청구월과 실제 결제일을 각각 기준으로 조회할 수 있습니다.',
        `<form id="payment-filter" class="toolbar">
            <select name="student_id" aria-label="결제 조회 학생">${opts(state.students,'student_id','name','','전체 학생')}</select>
            <label>내역 청구월 <input name="billing_month" type="month"></label>
            <label>결제 시작일 <input name="start_date" type="date"></label>
            <label>결제 종료일 <input name="end_date" type="date"></label>
            <button class="primary">내역 조회</button><button type="reset">전체 보기</button>
        </form><div id="payment-result"></div>`);
    $('#content').innerHTML='<div class="payment-panels">'+targets+history+'</div>';
    $('#target-filter').addEventListener('submit',event=>{event.preventDefault();loadPaymentTargets()});
    $('#target-filter').billing_month.addEventListener('change',()=>loadPaymentTargets());
    const form=$('#payment-filter');
    form.addEventListener('submit',event=>{event.preventDefault();loadPayments()});
    form.addEventListener('reset',()=>setTimeout(()=>{if(form.isConnected) loadPayments()},0));
    await Promise.all([loadPaymentTargets(token),loadPayments(token)]);
}
let targetRequest=0;
async function loadPaymentTargets(token=generation){
    const request=++targetRequest;
    const target=$('#target-results');
    const month=$('#target-filter').billing_month.value;
    target.textContent='결제 대상을 불러오는 중입니다…';
    try{
        const rows=await api('/api/payment-targets?'+new URLSearchParams({billing_month:month}));
        if(token!==generation||request!==targetRequest)return;
        target.innerHTML=table(['학생','반','과정','수강비','상태','관리'],rows.map(row=>tr([
            esc(row.student_name)+' (ID: '+row.student_id+')', esc(row.class_name), esc(row.course_name),
            money(row.billed_fee??row.fee), row.status?badge(row.status):'미발행',
            row.payment_id?'—':button('미납 등록','payment.issue',row.enrollment_id),
        ])),'해당 월의 결제 대상이 없습니다.');
        target.onclick=event=>{
            const issue=event.target.closest('[data-action="payment.issue"]');
            if(!issue)return;
            const row=rows.find(row=>row.enrollment_id===Number(issue.dataset.id));
            formDialog('미납 청구 등록',
                `<p class="note field full">${esc(row.student_name)} · ${esc(row.class_name)} · ${esc(month)} · ${money(row.fee)}</p>`,
                'payment.add',{student_id:row.student_id,class_id:row.class_id,billing_month:month,status:'UNPAID'},
                '',refreshPaymentPanels);
        };
    }catch(e){
        if(token===generation&&request===targetRequest)target.innerHTML=`<div class="error" role="alert">${esc(e.message)}</div>`;
    }
}
let paymentRequest=0;
async function loadPayments(token=generation){
    const request=++paymentRequest;
    try{
        const q=new URLSearchParams(new FormData($('#payment-filter')));
        const data=await api('/api/payments?'+q);
        if(token!==generation||request!==paymentRequest)return;
        $('#payment-result').innerHTML=table(['ID','학생명','반','결제 과정','청구월','금액','결제일','상태','관리'],
            data.rows.map(r=>tr([r.payment_id,esc(r.student_name),esc(r.class_name)||'—',esc(r.course_name),
                esc(r.billing_month?.slice(0,7))||'미지정',money(r.course_fee),esc(r.payment_date)||'—',
                badge(r.status),paymentAction(r)])))+
            `<div class="summary-strip"><span>조회 결과 ${data.rows.length}건 · 결제일 경계 포함</span><strong>수납 합계 ${money(data.total)}</strong></div>`;
    }catch(e){
        if(token===generation&&request===paymentRequest)$('#payment-result').innerHTML=`<div class="error" role="alert">${esc(e.message)}</div>`;
    }
}
async function refreshPaymentPanels(){
    if(page==='payments'&&$('#target-filter'))await Promise.all([loadPaymentTargets(),loadPayments()]);
}
function paymentAction(row){
    if(row.status==='UNPAID') return button('완납 처리','payment.paid',row.payment_id);
    if(row.status==='PAID') return button('환불 처리','payment.refund',row.payment_id);
    return '—';
}
function openDialog(title,html){$('#dialog-title').textContent=title;$('#dialog-body').innerHTML=html;$('#dialog').showModal()}
$('#close-dialog').onclick=()=>$('#dialog').close();$('#dialog').addEventListener('click',e=>{if(e.target===$('#dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close()}});
const field=(label,name,value='',type='text',required=false,extra='')=>`<div class="field"><label for="f-${name}">${label}${required?' *':''}</label><input id="f-${name}" name="${name}" type="${type}" value="${esc(value)}" ${required?'required':''} ${extra}></div>`;
const selectField=(label,name,options)=>`<div class="field"><label for="f-${name}">${label}</label><select id="f-${name}" name="${name}">${options}</select></div>`;
const statusOptions=(values,current)=>values.map(s=>`<option value="${s}" ${s===current?'selected':''}>${s==='ACTIVE'?'활성 / 수강 중':labels[s]}</option>`).join('');
function formDialog(title,fields,action,extra={},note='',onSaved=render){openDialog(title,`<p class="required">* 필수 입력 항목</p><form id="editor"><div class="form-grid">${fields}</div>${note?`<p class="note">${note}</p>`:''}<div id="form-error" role="alert"></div><div class="form-actions"><button type="button" id="cancel">취소</button><button class="primary" id="save">저장</button></div></form>`);$('#cancel').onclick=()=>$('#dialog').close();$('#editor').addEventListener('submit',async e=>{e.preventDefault();const data={...Object.fromEntries(new FormData(e.target)),...extra};const save=$('#save');save.disabled=true;try{await api('/api/'+action,data);$('#dialog').close();toast('저장되었습니다.');await onSaved()}catch(err){$('#form-error').innerHTML=`<div class="error">${esc(err.message)}</div>`}finally{save.disabled=false}})}
function gradeField(current){
    const options='<option value="">미지정</option>'+state.grade_levels.map(grade=>
        `<option value="${esc(grade)}" ${grade===current?'selected':''}>${esc(grade)}</option>`).join('');
    return selectField('학년','grade',options);
}
function studentEditor(r={}){formDialog(r.student_id?'학생 정보 수정':'새 학생 등록',field('이름','name',r.name,'text',true)+field('학교','school',r.school)+gradeField(r.grade)+field('등록일','day_of_admission',r.day_of_admission??today(),'date')+field('연락처','contact_number',r.contact_number,'tel')+selectField('학생 분류','student_classification',statusOptions(['ACTIVE','INACTIVE','BLACK'],r.student_classification||'ACTIVE')),'student.save',r.student_id?{student_id:r.student_id}:{},'블랙리스트 학생은 신규 수강 등록과 결제가 제한됩니다. 분류를 바꿔도 기존 수강 상태는 자동으로 변경되지 않습니다.')}
function teacherEditor(r={}){formDialog(r.teacher_id?'선생님 정보 수정':'새 선생님 등록',field('이름','name',r.name,'text',true)+field('연락처','contact_number',r.contact_number,'tel'),'teacher.save',r.teacher_id?{teacher_id:r.teacher_id}:{})}
function courseEditor(r={}){formDialog(r.course_id?'수강 과정 수정':'새 수강 과정',field('과정명','name',r.name,'text',true)+field('수강비 (원)','fee',r.fee??'','number',true,'min="0" step="1"'),'course.save',r.course_id?{course_id:r.course_id}:{},'수강비는 0원 이상입니다. 변경된 가격은 이후 결제에 적용되며 과거 결제 금액은 유지됩니다.')}
function classEditor(r={}){const edit=!!r.class_id;formDialog(edit?'반 정보 수정':'새 반 개설',field('반 이름','class_name',r.class_name,'text',true)+gradeField(r.grade)+selectField('수강 과정 *','course_id',opts(state.courses,'course_id','name',r.course_id))+selectField('담당 선생님','teacher_id',opts(state.teachers,'teacher_id','name',r.teacher_id,'미지정 (공석)'))+(edit?'':selectField('반 유형','kind','<option value="regular">정규반</option><option value="short">특강</option>')+`<div class="field full" id="period" hidden><div class="form-grid">${field('특강 시작일','start_date','','date')+field('특강 종료일','end_date','','date')}</div></div>`),'class.save',edit?{class_id:r.class_id}:{},edit?'수강 과정과 특강 기간은 유지됩니다. 선생님을 미지정으로 바꾸면 공석 처리됩니다.':'시간표는 반 개설 후 목록의 시간표 버튼에서 등록하세요.');$('#f-course_id').required=true;if(edit)$('#f-course_id').disabled=true;else $('#f-kind').onchange=()=>{const short=$('#f-kind').value==='short';$('#period').hidden=!short;$('#f-start_date').required=short;$('#f-end_date').required=short}}
function enrollmentEditor(){formDialog('새 수강 등록',selectField('학생 *','student_id',opts(state.students.filter(r=>r.student_classification!=='BLACK'),'student_id','name'))+selectField('반 *','class_id',opts(state.classes,'class_id','class_name'))+field('수강 등록일','enrolled_date',today(),'date'),'enrollment.add',{},'같은 학생은 같은 반에 중복 등록할 수 없습니다. 재수강은 기존 수강의 상태를 변경하세요.');$('#f-student_id').required=true;$('#f-class_id').required=true}
function enrollmentStatus(r){formDialog('수강 상태 변경',`<div class="field full"><p class="note">${esc(r.student_name)} · ${esc(r.class_name)}</p></div>`+selectField('수강 상태','status',statusOptions(['ACTIVE','COMPLETED','CANCELED'],r.status)),'enrollment.status',{enrollment_id:r.enrollment_id},'수료·취소 시 결제 등록 대상에서 제외됩니다. 기존 결제 내역과 최초 수강 등록일은 유지됩니다.')}
function paymentEditor(){
    const month=$('#target-filter')?.billing_month.value||today().slice(0,7);
    const fields=selectField('학생 *','student_id',opts(state.students.filter(s=>s.student_classification!=='BLACK'),'student_id','name'))
        +field('청구월','billing_month',month,'month',true)
        +selectField('결제 대상 반 *','class_id','<option value="">학생을 먼저 선택하세요</option>')
        +field('결제 금액 (원)','amount','','text',false,'readonly')
        +selectField('결제 상태','status',statusOptions(['PAID','UNPAID'],'PAID'))
        +field('결제일','payment_date',today(),'date');
    formDialog('수강료 결제 등록',fields,'payment.add',{},
        '청구월을 기준으로 미발행 수강을 선택합니다. 선택한 반의 현재 수강비를 저장합니다.',refreshPaymentPanels);
    const student=$('#f-student_id'), billingMonth=$('#f-billing_month'), target=$('#f-class_id');
    const amount=$('#f-amount'), save=$('#save'), error=$('#form-error');
    student.required=true;
    target.required=true;
    target.disabled=true;
    save.disabled=true;
    let active=[],request=0;
    async function loadClasses(){
        const version=++request;
        error.textContent='';
        target.disabled=true;
        target.innerHTML='<option value="">해당 월의 미발행 수강 없음</option>';
        amount.value='';
        save.disabled=true;
        if(!student.value||!billingMonth.value)return;
        try{
            const query=new URLSearchParams({student_id:student.value,billing_month:billingMonth.value});
            const rows=await api('/api/payment-targets?'+query);
            if(version!==request||!target.isConnected)return;
            active=rows.filter(row=>!row.payment_id);
            target.innerHTML=opts(active,'class_id','class_name','','반을 선택하세요');
            target.disabled=!active.length;
        }catch(e){
            if(version===request&&target.isConnected)error.textContent=e.message;
        }
    }
    student.onchange=billingMonth.onchange=loadClasses;
    target.onchange=()=>{
        const row=active.find(row=>String(row.class_id)===target.value);
        amount.value=row?money(row.fee):'';
        save.disabled=!row;
    };
    $('#f-status').onchange=()=>{$('#f-payment_date').disabled=$('#f-status').value==='UNPAID'};
}
function paymentStatusEditor(id,status){
    const paid=status==='PAID';
    const fields=paid?field('실제 결제일','payment_date',today(),'date',true):
        '<p class="note field full">선택한 결제를 전액 환불 상태로 기록합니다. 최초 결제일과 금액은 보존됩니다.</p>';
    formDialog(paid?'완납 처리':'환불 처리',fields,'payment.status',{payment_id:id,status},'',refreshPaymentPanels);
}
async function studentHistory(id){const r=state.students.find(s=>s.student_id===id),d=await api('/api/student?id='+id);const total=d.enrollments.filter(e=>e.status==='ACTIVE').reduce((n,e)=>n+e.fee,0);openDialog(`${r.name} · 수강 내역`, `<div class="note">학생 ID ${id} · 모든 수강 상태를 표시합니다.<br>현재 수강비 합계 <b>${money(total)}</b> · 수강 중인 반의 현재 가격 기준이며 납부액이 아닙니다.</div>`+table(['반 이름','과정','현재 수강비','등록일','상태'],d.enrollments.map(e=>tr([esc(e.class_name),esc(e.course_name),money(e.fee),esc(e.enrolled_date),badge(e.status)]))))}
async function classRoster(id){const r=state.classes.find(c=>c.class_id===id),d=await api('/api/class?id='+id);openDialog(`${r.class_name} · 학생 명단`,`<p class="note">총 ${d.students.length}명 · 수료·취소 상태를 포함합니다.</p>`+table(['학생 ID','이름','학교','수강 상태'],d.students.map(s=>tr([s.student_id,esc(s.name),esc(s.school)||'—',badge(s.status)]))))}
async function scheduleEditor(id){const r=state.classes.find(c=>c.class_id===id),d=await api('/api/class?id='+id),days=['MON','TUE','WED','THU','FRI','SAT','SUN'],names=['월요일','화요일','수요일','목요일','금요일','토요일','일요일'];openDialog(`${r.class_name} · 주간 시간표`,`<p class="note">${esc(r.course_name)} · 담당 ${esc(r.teacher_name)||'미지정'}<br>체크한 요일만 저장합니다. 체크를 해제하면 해당 요일의 수업이 삭제됩니다.</p><form id="schedule-form">${days.map((day,i)=>{const t=d.timetable.find(t=>t.day_of_class===day);return `<div class="schedule"><label><input type="checkbox" name="${day}" ${t?'checked':''}>${names[i]}</label><input aria-label="${names[i]} 시작 시간" type="time" id="${day}-start" value="${t?.start_time||''}" ${t?'required':'disabled'}><input aria-label="${names[i]} 종료 시간" type="time" id="${day}-end" value="${t?.end_time||''}" ${t?'required':'disabled'}></div>`}).join('')}<p class="note">종료 시간은 시작 시간 이후여야 합니다. 자정을 넘기는 수업은 지원하지 않습니다.</p><div id="form-error" role="alert"></div><div class="form-actions"><button type="button" id="cancel">취소</button><button class="primary" id="save">시간표 저장</button></div></form>`);$('#cancel').onclick=()=>$('#dialog').close();days.forEach(day=>{$(`[name=${day}]`).onchange=e=>{for(const key of ['start','end']){const input=$(`#${day}-${key}`);input.disabled=!e.target.checked;input.required=e.target.checked}}});$('#schedule-form').onsubmit=async e=>{e.preventDefault();const schedule={};days.forEach(day=>{if($(`[name=${day}]`).checked)schedule[day]=[$(`#${day}-start`).value,$(`#${day}-end`).value]});$('#save').disabled=true;try{await api('/api/timetable.save',{class_id:id,schedule});$('#dialog').close();toast('시간표가 저장되었습니다.')}catch(err){$('#form-error').innerHTML=`<div class="error">${esc(err.message)}</div>`;$('#save').disabled=false}}}
$('#primary').onclick=()=>({students:studentEditor,teachers:teacherEditor,courses:courseEditor,classes:classEditor,enrollments:enrollmentEditor,payments:paymentEditor}[page]?.());
document.addEventListener('click',async e=>{const b=e.target.closest('[data-action]');if(!b)return;const id=Number(b.dataset.id);try{switch(b.dataset.action){case 'retry':await render();break;case 'student.edit':studentEditor(state.students.find(r=>r.student_id===id));break;case 'student.history':await studentHistory(id);break;case 'teacher.edit':teacherEditor(state.teachers.find(r=>r.teacher_id===id));break;case 'course.edit':courseEditor(state.courses.find(r=>r.course_id===id));break;case 'class.edit':classEditor(state.classes.find(r=>r.class_id===id));break;case 'class.roster':await classRoster(id);break;case 'class.schedule':await scheduleEditor(id);break;case 'enrollment.edit':enrollmentStatus(state.enrollments.find(r=>r.enrollment_id===id));break;case 'payment.paid':paymentStatusEditor(id,'PAID');break;case 'payment.refund':paymentStatusEditor(id,'REFUNDED');break}}catch(err){toast(err.message)}});
$('.skip').addEventListener('click',e=>{e.preventDefault();$('#main').focus()});
window.addEventListener('hashchange',render);render();
