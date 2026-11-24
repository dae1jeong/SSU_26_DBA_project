// Run: node --test tests/test_page_requests.cjs
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function app() {
    const elements = new Map();
    function element(key) {
        if (!elements.has(key)) elements.set(key, {
            innerHTML: '', classList: {toggle() {}},
            addEventListener() {}, setAttribute() {}, replaceChildren() {},
            querySelector() {return element('child');},
        });
        return elements.get(key);
    }
    const context = vm.createContext({
        document: {querySelector: element, querySelectorAll: () => [],
            addEventListener() {}, createElement: () => element('created')},
        window: {addEventListener() {}}, location: {hash: ''},
        setInterval() {}, setTimeout() {}, clearTimeout() {}, URLSearchParams,
    });
    vm.runInContext(fs.readFileSync('backend/web/app.js', 'utf8'), context);
    vm.runInContext(`
        var requests = [], drawn, edited;
        api = async (url) => {
            requests.push(url);
            if (url === '/api/grade-levels') return [];
            if (url.startsWith('/api/student-detail')) return {student_id:1, day_of_admission:'2026-01-01'};
            return [];
        };
        mountListing = () => {drawn = listing()};
        dashboard = () => {drawn = 'dashboard'};
        payments = async () => {drawn = 'payments'};
    `, context);
    return context;
}

test('each menu requests only its list and required metadata', async () => {
    for (const page of ['students','teachers','courses','classes','enrollments','dashboard','payments']) {
        const ctx = app();
        ctx.location.hash = '#' + page;
        await vm.runInContext('render()', ctx);
        const expected = page === 'payments' ? ['/api/options?kind=students'] : ['/api/' + page];
        if (['students','classes'].includes(page)) expected.push('/api/grade-levels');
        assert.deepEqual(Array.from(ctx.requests), expected);
        assert.ok(ctx.drawn, page + ' rendered');
    }
});

test('teacher and course rows render without loading classes', () => {
    const ctx = app();
    const teacher = vm.runInContext(`page='teachers'; state={teachers:[{teacher_id:1,name:'T',class_names:['A']}]}; listing()`, ctx);
    assert.match(teacher, /A/);
    const course = vm.runInContext(`page='courses'; state={courses:[{course_id:1,name:'C',fee:100,class_count:3}]}; listing()`, ctx);
    assert.match(course, /3개/);
});

test('student edit loads full details, including admission date', async () => {
    const ctx = app();
    vm.runInContext('studentEditor = row => {edited = row}', ctx);
    await vm.runInContext("prepareEditor('students', {student_id:1})", ctx);
    assert.deepEqual(Array.from(ctx.requests), ['/api/student-detail?id=1']);
    assert.equal(ctx.edited.day_of_admission, '2026-01-01');
});

test('class and enrollment forms load only their selection options', async () => {
    for (const [kind, options] of [['classes',['courses','teachers']], ['enrollments',['students','classes']], ['payments',['students']]]) {
        const ctx = app();
        vm.runInContext('classEditor = enrollmentEditor = paymentEditor = () => {edited = true}', ctx);
        await vm.runInContext(`prepareEditor('${kind}')`, ctx);
        assert.deepEqual(Array.from(ctx.requests), options.map(k=>'/api/options?kind='+k));
        assert.equal(ctx.edited, true);
    }
});

test('late menu responses cannot overwrite the current page state', async () => {
    const ctx = app();
    vm.runInContext(`var finishStudents; api = url => url === '/api/students'
        ? new Promise(resolve => {finishStudents=resolve}) : Promise.resolve([])`, ctx);
    ctx.location.hash = '#students';
    const first = vm.runInContext('render()', ctx);
    ctx.location.hash = '#teachers';
    await vm.runInContext('render()', ctx);
    ctx.finishStudents([{student_id:1}]);
    await first;
    assert.equal(vm.runInContext('state.students', ctx), undefined);
    assert.ok(vm.runInContext('state.teachers', ctx));
});
