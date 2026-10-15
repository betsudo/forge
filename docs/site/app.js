'use strict';
const menu = document.querySelector('#menu-toggle');
const sidebar = document.querySelector('#sidebar');
menu.addEventListener('click', () => {
  const open = menu.getAttribute('aria-expanded') !== 'true';
  menu.setAttribute('aria-expanded', String(open));
  sidebar.classList.toggle('open', open);
});
const links = [...document.querySelectorAll('nav a')];
function select(id) {
  links.forEach(link => {
    const active = link.hash === `#${id}`;
    link.classList.toggle('active', active);
    if (active) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  });
}
links.forEach(link => link.addEventListener('click', () => {
  menu.setAttribute('aria-expanded', 'false');
  sidebar.classList.remove('open');
  select(link.hash.slice(1));
}));
select(location.hash.slice(1) || 'overview');
const observer = new IntersectionObserver(entries => {
  const visible = entries.filter(entry => entry.isIntersecting);
  if (visible.length) select(visible[0].target.id);
}, {rootMargin: '-10% 0px -65% 0px'});
document.querySelectorAll('section, #overview').forEach(section => observer.observe(section));
let copyTimer;
document.querySelectorAll('.copy').forEach(button => button.addEventListener('click', async () => {
  const status = document.querySelector('#copy-status');
  try {
    await navigator.clipboard.writeText(button.parentElement.querySelector('code').textContent);
    status.textContent = 'Command copied';
  } catch {
    status.textContent = 'Select the command to copy it manually';
  }
  status.classList.add('visible');
  clearTimeout(copyTimer);
  copyTimer = setTimeout(() => status.classList.remove('visible'), 2400);
}));
