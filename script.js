const form = document.getElementById('todo-form');
const input = document.getElementById('todo-input');
const list = document.getElementById('todo-list');
const refreshBtn = document.getElementById('refresh-todos');

function renderTodos(todos) {
  list.innerHTML = '';

  const ding = new Audio('ding.mp3');

  todos.forEach((todo, index) => {
    if (todo.completed) return; // ✅ Auto-hide completed items

    const li = document.createElement('li');

    // Checkbox
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'todo-checkbox';
    checkbox.checked = false;

    checkbox.addEventListener('change', () => {
      if (checkbox.checked) {
        ding.currentTime = 0;
        ding.play();
        completeAndHideTodo(index);
      }
    });

    const span = document.createElement('span');
    span.textContent = todo.text;
    span.style.flex = '1';
    span.style.marginLeft = '10px';

    li.appendChild(checkbox);
    li.appendChild(span);
    list.appendChild(li);
  });
}

function getTodos(callback) {
  chrome.storage.local.get(['todos'], (result) => {
    callback(result.todos || []);
  });
}

function saveTodos(todos) {
  chrome.storage.local.set({ todos });
}

function addTodo(text) {
  getTodos((todos) => {
    todos.push({ text, completed: false });
    saveTodos(todos);
    renderTodos(todos);
  });
}

function removeTodo(index) {
  getTodos((todos) => {
    todos.splice(index, 1);
    saveTodos(todos);
    renderTodos(todos);
  });
}

function completeAndHideTodo(index) {
  getTodos((todos) => {
    todos[index].completed = true;
    saveTodos(todos);
    renderTodos(todos);
  });
}

// Fetch tasks from your Python Flask backend
async function fetchTasksFromBackend() {
  try {
    const response = await fetch('http://localhost:5000/todos');
    if (!response.ok) throw new Error('Network response was not ok');
    const taskStrings = await response.json();
    
    // Convert array of strings to array of objects with text and completed properties
    const todos = taskStrings.map(task => ({
      text: task,
      completed: false
    }));
    
    return todos;
  } catch (error) {
    console.error('Failed to fetch tasks:', error);
    alert('Error: Make sure your Flask server is running on http://localhost:5000');
    return [];
  }
}

// Load todos from Chrome storage and render
function loadTodos() {
  getTodos(renderTodos);
}

// Refresh todos by fetching from backend and saving locally
async function refreshTodos() {
  const newTodos = await fetchTasksFromBackend();
  saveTodos(newTodos);
  renderTodos(newTodos);
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  const value = input.value.trim();
  if (value) {
    addTodo(value);
    input.value = '';
  }
});

refreshBtn.addEventListener('click', () => {
  refreshTodos();
});

document.addEventListener('DOMContentLoaded', () => {
  loadTodos();
});
