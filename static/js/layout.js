// AI Tutor Website JavaScript with Enhanced Hover Responsiveness and Smooth Header Hide/Show

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all functionality
    initScrollAnimations();
    initSmoothScrolling();
    initHeaderScroll();
    initFastHoverEffects();
});

// Enhanced hover effects for immediate response
function initFastHoverEffects() {
    // Add immediate hover feedback for buttons
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px) scale(1.05)';
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
        
        // Add quick tap feedback
        btn.addEventListener('mousedown', function() {
            this.style.transform = 'translateY(-1px) scale(0.98)';
        });
        
        btn.addEventListener('mouseup', function() {
            this.style.transform = 'translateY(-3px) scale(1.05)';
        });
    });

    // Enhanced function card hover effects
    const functionCards = document.querySelectorAll('.function-card');
    functionCards.forEach(card => {
        const icon = card.querySelector('.function-icon');
        const title = card.querySelector('h3');
        
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-15px) scale(1.02)';
            this.style.boxShadow = '0 25px 50px rgba(0, 0, 0, 0.2)';
            this.style.borderColor = '#87CEEB';
            
            if (icon) {
                icon.style.transform = 'scale(1.1)';
                icon.style.color = '#2c3e50';
            }
            
            if (title) {
                title.style.color = '#87CEEB';
            }
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.boxShadow = '';
            this.style.borderColor = '';
            
            if (icon) {
                icon.style.transform = '';
                icon.style.color = '';
            }
            
            if (title) {
                title.style.color = '';
            }
        });
    });

    // Enhanced social links hover
    const socialLinks = document.querySelectorAll('.social-links a');
    socialLinks.forEach(link => {
        link.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px) scale(1.1)';
            this.style.boxShadow = '0 5px 15px rgba(152, 251, 152, 0.4)';
        });
        
        link.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.boxShadow = '';
        });
    });

    // Add hover effect for logo
    const logo = document.querySelector('.nav-brand h2');
    if (logo) {
        logo.addEventListener('mouseenter', function() {
            this.style.color = '#1a7599';
           
        });
        
        logo.addEventListener('mouseleave', function() {
            this.style.color = '';
            this.style.transform = '';
        });
    }

    // Add subtle hover for hero image
    const heroImage = document.querySelector('.hero-image');
    if (heroImage) {
        heroImage.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.02)';
            this.style.boxShadow = '0 25px 50px rgba(0, 0, 0, 0.15)';
        });
        
        heroImage.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.boxShadow = '';
        });
    }
}

// Scroll Animation Observer
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('show');
            }
        });
    }, observerOptions);

    // Observe all animation elements
    const animateElements = document.querySelectorAll('.animate-up, .slide-right');
    animateElements.forEach(el => {
        observer.observe(el);
    });

    // Stagger animation for function cards
    const functionCards = document.querySelectorAll('.function-card');
    functionCards.forEach((card, index) => {
        card.style.transitionDelay = `${index * 0.01}s`; //time-delay for the animation when mouse hover to the card
    });
}

// Smooth scrolling for anchor links
function initSmoothScrolling() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            // Skip if href is just "#"
            if (href === '#') {
                e.preventDefault();
                return;
            }
            
            const target = document.querySelector(href);
            
            if (target) {
                e.preventDefault();
                
                const headerHeight = document.querySelector('.header').offsetHeight;
                const targetPosition = target.offsetTop - headerHeight;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// Enhanced header scroll effect with hide/show functionality
function initHeaderScroll() {
    const header = document.querySelector('.header');
    let lastScrollTop = 0;
    let scrollThreshold = 80; // Minimum scroll distance before hiding header
    let isHeaderVisible = true;
    
    // Add transition property to header for smooth animation
    header.style.transition = 'transform 0.3s ease-in-out, background-color 0.3s ease';
    
    const throttledScrollHandler = throttle(function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Add background opacity based on scroll
        if (scrollTop > 50) {
            header.style.backgroundColor = 'rgba(135, 206, 235, 0.95)';
            header.style.backdropFilter = 'blur(10px)';
        } else {
            header.style.backgroundColor = '';
            header.style.backdropFilter = '';
        }
        
        // Hide/Show header based on scroll direction
        if (scrollTop > scrollThreshold) {
            if (scrollTop > lastScrollTop && isHeaderVisible) {
                // Scrolling down - hide header
                header.style.transform = 'translateY(-100%)';
                isHeaderVisible = false;
            } else if (scrollTop < lastScrollTop && !isHeaderVisible) {
                // Scrolling up - show header
                header.style.transform = 'translateY(0)';
                isHeaderVisible = true;
            }
        } else {
            // Always show header when near top of page
            if (!isHeaderVisible) {
                header.style.transform = 'translateY(0)';
                isHeaderVisible = true;
            }
        }
        
        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop; // Prevent negative values
    }, 16); // ~60fps throttling
    
    window.addEventListener('scroll', throttledScrollHandler);
    
    // Show header when mouse moves to top of screen
    document.addEventListener('mousemove', function(e) {
        if (e.clientY <= 100 && !isHeaderVisible && window.pageYOffset > scrollThreshold) {
            header.style.transform = 'translateY(0)';
            isHeaderVisible = true;
        }
    });
}

// Add floating animation to hero elements
function addFloatingAnimation() {
    const floatingElements = document.querySelectorAll('.ai-icon');
    
    floatingElements.forEach(element => {
        let direction = 1;
        let position = 0;
        
        setInterval(() => {
            position += direction * 0.5;
            
            if (position > 10) direction = -1;
            if (position < -10) direction = 1;
            
            element.style.transform = `translateY(${position}px)`;
        }, 50);
    });
}

// Utility function for throttling scroll events
function throttle(func, wait) {
    let timeout;
    let lastTime = 0;
    
    return function executedFunction(...args) {
        const now = Date.now();
        
        if (now - lastTime >= wait) {
            func.apply(this, args);
            lastTime = now;
        } else {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                func.apply(this, args);
                lastTime = Date.now();
            }, wait - (now - lastTime));
        }
    };
}

// Enhanced scroll reveal with different animation types
function initEnhancedScrollAnimations() {
    const revealElements = document.querySelectorAll('.animate-up, .slide-right');
    
    const revealElementOnScroll = throttle(() => {
        revealElements.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;
            const elementVisible = 150;
            
            if (elementTop < window.innerHeight - elementVisible) {
                element.classList.add('show');
            }
        });
    }, 100);
    
    window.addEventListener('scroll', revealElementOnScroll);
    
    // Initial check for elements already in view
    revealElementOnScroll();
}

// Add loading animation
window.addEventListener('load', function() {
    document.body.classList.add('loaded');
    
    // Optional: Add page load animation
    const pageElements = document.querySelectorAll('.animate-up');
    pageElements.forEach((element, index) => {
        setTimeout(() => {
            element.classList.add('show');
        }, index * 100);
    });
});

// Call initialization functions
document.addEventListener('DOMContentLoaded', function() {
    initScrollAnimations();
    initSmoothScrolling();
    initHeaderScroll();
});