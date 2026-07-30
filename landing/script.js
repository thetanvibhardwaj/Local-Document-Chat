// --- 3D TILT EFFECT FOR CARDS & HERO VISUAL ---
const tiltCards = document.querySelectorAll('[data-tilt], #hero-tilt-card');

tiltCards.forEach(card => {
    card.addEventListener('mousemove', e => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left; // x coordinate inside element
        const y = e.clientY - rect.top;  // y coordinate inside element
        
        const width = rect.width;
        const height = rect.height;
        
        // Calculate tilt percentages (-10 to 10 degrees)
        const tiltX = -( (y - (height / 2)) / (height / 2) ) * 10;
        const tiltY = ( (x - (width / 2)) / (width / 2) ) * 10;
        
        card.style.transform = `perspective(1000px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) scale3d(1.02, 1.02, 1.02)`;
    });
    
    card.addEventListener('mouseleave', () => {
        card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
    });
});


// --- INTERSECTION OBSERVER FOR SCROLL SLIDE-INS ---
const animatedElements = document.querySelectorAll('.fade-in, .fade-in-right, .fade-in-up, .slide-in-left');

const observerOptions = {
    threshold: 0.15,
    rootMargin: "0px 0px -50px 0px"
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('show');
            // Once animated, we don't need to observe it anymore
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

animatedElements.forEach(el => observer.observe(el));


// --- TAB CONTROLLER FOR PIPELINES ---
function switchPipeline(tabName) {
    // Toggle active buttons
    const buttons = document.querySelectorAll('#pipeline .tab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    // Find matching button to activate
    const activeBtn = Array.from(buttons).find(btn => btn.textContent.toLowerCase().includes(tabName.toLowerCase()));
    if (activeBtn) activeBtn.classList.add('active');
    
    // Toggle active flows
    const flows = document.querySelectorAll('.pipeline-flow');
    flows.forEach(flow => flow.classList.remove('active-flow'));
    
    const activeFlow = document.getElementById(`pipeline-${tabName}`);
    if (activeFlow) {
        activeFlow.classList.add('active-flow');
        
        // Re-run observer on active steps to slide them in dynamically
        const steps = activeFlow.querySelectorAll('.flow-step');
        steps.forEach(step => step.classList.add('show'));
    }
}


// --- TAB CONTROLLER FOR DATABASE SCHEMAS ---
function switchSchema(tabName) {
    const section = document.getElementById('architecture');
    const buttons = section.querySelectorAll('.tab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    const activeBtn = Array.from(buttons).find(btn => btn.textContent.toLowerCase().includes(tabName.toLowerCase()));
    if (activeBtn) activeBtn.classList.add('active');
    
    const viewers = section.querySelectorAll('.schema-viewer');
    viewers.forEach(view => view.classList.remove('active-schema'));
    
    const activeViewer = document.getElementById(`schema-${tabName}`);
    if (activeViewer) activeViewer.classList.add('active-schema');
}


// --- TAB CONTROLLER FOR API SANDBOX ---
function switchApi(tabName) {
    const section = document.getElementById('api');
    const buttons = section.querySelectorAll('.tab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    const activeBtn = Array.from(buttons).find(btn => btn.textContent.toLowerCase().includes(tabName.toLowerCase()));
    if (activeBtn) activeBtn.classList.add('active');
    
    const viewers = section.querySelectorAll('.api-viewer');
    viewers.forEach(view => view.classList.remove('active-api'));
    
    const activeViewer = document.getElementById(`api-${tabName}`);
    if (activeViewer) activeViewer.classList.add('active-api');
}
