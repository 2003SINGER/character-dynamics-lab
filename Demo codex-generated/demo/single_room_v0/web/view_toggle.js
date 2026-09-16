(() => {
  const debug = document.querySelector('.debug');
  const note = document.getElementById('view-note');
  const button = document.createElement('button');
  button.id = 'view-toggle';
  button.textContent = 'Player View';
  document.querySelector('header').appendChild(button);
  let developer = true;
  button.onclick = () => {
    developer = !developer;
    debug.querySelectorAll('.card:first-of-type').forEach((card) => { card.hidden = !developer; });
    button.textContent = developer ? 'Player View' : 'Developer View';
    note.textContent = developer
      ? 'Developer View: W and actor-local O are both visible.'
      : 'Player View: actor-visible O, S, action and time are shown; W-only fields are hidden.';
  };
})();
