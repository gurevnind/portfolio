/* Минимальный рантайм страниц портфолио.
   Заменяет support.js референсов: та же модель Component/renderVals/setState,
   но без React — привязки размечены сборщиком (build.py) data-атрибутами. */
(function () {
  'use strict';

  var UNITLESS = { opacity: 1, zIndex: 1, flex: 1, flexGrow: 1, flexShrink: 1, fontWeight: 1, lineHeight: 1, order: 1, zoom: 1 };

  function append(el, kids) {
    for (var i = 0; i < kids.length; i++) {
      var k = kids[i];
      if (k == null || k === false || k === true) continue;
      if (Array.isArray(k)) append(el, k);
      else el.appendChild(k instanceof Node ? k : document.createTextNode(String(k)));
    }
  }

  // Подмножество React.createElement, достаточное для heroFlowers / zoomImg.
  var React = {
    createElement: function (tag, props) {
      var el = document.createElement(tag);
      props = props || {};
      for (var k in props) {
        var v = props[k];
        if (k === 'key' || v == null) continue;
        if (k === 'style') {
          for (var s in v) {
            var sv = v[s];
            if (s.indexOf('--') === 0) el.style.setProperty(s, sv);
            else el.style[s] = typeof sv === 'number' && !UNITLESS[s] ? sv + 'px' : sv;
          }
        } else if (/^on[A-Z]/.test(k) && typeof v === 'function') {
          el.addEventListener(k.slice(2).toLowerCase(), v);
        } else if (k === 'className') {
          el.className = v;
        } else {
          el.setAttribute(k, v === true ? '' : String(v));
        }
      }
      append(el, Array.prototype.slice.call(arguments, 2));
      return el;
    },
    createRef: function () { return { current: null }; }
  };
  window.React = React;

  // Обновляет живой узел до вида нового, сохраняя его (чтобы работали CSS-переходы).
  function morph(a, b) {
    if (a.nodeType === 3 && b.nodeType === 3) { if (a.nodeValue !== b.nodeValue) a.nodeValue = b.nodeValue; return a; }
    if (a.nodeType !== 1 || b.nodeType !== 1 || a.tagName !== b.tagName) { a.replaceWith(b); return b; }
    var i, at;
    for (i = a.attributes.length - 1; i >= 0; i--) {
      at = a.attributes[i].name;
      if (!b.hasAttribute(at)) a.removeAttribute(at);
    }
    for (i = 0; i < b.attributes.length; i++) {
      at = b.attributes[i];
      if (a.getAttribute(at.name) !== at.value) a.setAttribute(at.name, at.value);
    }
    var ak = a.childNodes, bk = Array.prototype.slice.call(b.childNodes);
    for (i = 0; i < bk.length; i++) {
      if (i < ak.length) morph(ak[i], bk[i]);
      else a.appendChild(bk[i]);
    }
    while (ak.length > bk.length) a.removeChild(a.lastChild);
    return a;
  }

  function setSlot(el, v) {
    if (v instanceof Node) {
      if (el.firstChild === v && el.childNodes.length === 1) return;
      if (el.childNodes.length === 1 && el.firstChild.nodeType === 1 && v.nodeType === 1) {
        morph(el.firstChild, v);
        return;
      }
      el.textContent = '';
      el.appendChild(v);
      return;
    }
    var t = v == null || v === false ? '' : String(v);
    if (el.textContent !== t || el.children.length) el.textContent = t;
  }

  function get(scope, expr) {
    if (expr === 'true') return true;
    if (expr === 'false') return false;
    var parts = expr.split('.'), v = scope;
    for (var i = 0; i < parts.length && v != null; i++) v = v[parts[i]];
    return v;
  }

  function pairs(s) {
    return s.split(';').filter(Boolean).map(function (p) {
      var i = p.indexOf(':');
      return [p.slice(0, i), p.slice(i + 1)];
    });
  }

  function bindEvents(el) {
    if (el.__dcOn) return;
    el.__dcOn = true;
    pairs(el.getAttribute('data-on')).forEach(function (p) {
      el.addEventListener(p[0], function (e) {
        var fn = get(el.__dcScope, p[1]);
        if (typeof fn === 'function') fn(e);
      });
    });
  }

  function setItemVars(nodes, item) {
    if (!item || typeof item !== 'object') return;
    nodes.forEach(function (n) {
      if (n.nodeType !== 1) return;
      for (var k in item) {
        var v = item[k];
        if (typeof v === 'string' || typeof v === 'number') n.style.setProperty('--i-' + k, String(v));
      }
    });
  }

  function walk(node, scope) {
    for (var c = node.firstElementChild; c; c = c.nextElementSibling) visit(c, scope);
  }

  function visit(el, scope) {
    if (el.tagName === 'TEMPLATE') return;
    if (el.tagName === 'DC-FOR') return renderFor(el, scope);
    if (el.tagName === 'DC-IF') {
      var on = !!get(scope, el.getAttribute('data-if'));
      if (on === el.hidden) el.hidden = !on;
      if (on) walk(el, scope);
      return;
    }
    var a;
    if ((a = el.getAttribute('data-t')) !== null) setSlot(el, get(scope, a));
    if ((a = el.getAttribute('data-a')) !== null) {
      pairs(a).forEach(function (p) {
        var v = get(scope, p[1]);
        if (v == null || v === false) el.removeAttribute(p[0]);
        else if (el.getAttribute(p[0]) !== String(v)) el.setAttribute(p[0], String(v));
      });
    }
    if ((a = el.getAttribute('data-ref')) !== null) { var r = get(scope, a); if (r) r.current = el; }
    if (el.hasAttribute('data-on')) { el.__dcScope = scope; bindEvents(el); }
    if (el.getAttribute('data-t') === null) walk(el, scope);
  }

  function renderFor(el, scope) {
    var list = get(scope, el.getAttribute('data-for'));
    if (!Array.isArray(list)) list = [];
    var as = el.getAttribute('data-as') || 'item';
    var tpl = el.querySelector(':scope > template');
    var groups = el.__dcGroups || (el.__dcGroups = []);
    while (groups.length > list.length) groups.pop().forEach(function (n) { n.remove(); });
    while (groups.length < list.length) {
      var frag = tpl.content.cloneNode(true);
      groups.push(Array.prototype.slice.call(frag.childNodes));
      el.appendChild(frag);
    }
    list.forEach(function (item, i) {
      var sub = Object.create(scope);
      sub[as] = item;
      setItemVars(groups[i], item);
      groups[i].forEach(function (n) { if (n.nodeType === 1) visit(n, sub); });
    });
  }

  function DCLogic(props) {
    this.props = props || {};
    this.state = {};
  }
  DCLogic.prototype.setState = function (u) {
    var self = this;
    (self.__q || (self.__q = [])).push(u);
    if (self.__pending) return;
    self.__pending = true;
    Promise.resolve().then(function () {
      self.__pending = false;
      var q = self.__q; self.__q = [];
      var changed = false;
      q.forEach(function (x) {
        var p = typeof x === 'function' ? x.call(self, self.state, self.props) : x;
        if (p != null) { self.state = Object.assign({}, self.state, p); changed = true; }
      });
      if (changed) self.__render();
    });
  };
  DCLogic.prototype.__render = function () {
    var vals = this.renderVals();
    var root = document.documentElement.style;
    (window.DC_VARS || []).forEach(function (k) {
      var v = vals[k];
      if (typeof v === 'string' || typeof v === 'number') {
        var s = String(v);
        if (root.getPropertyValue('--v-' + k) !== s) root.setProperty('--v-' + k, s);
      }
    });
    walk(document.body, vals);
  };
  window.DCLogic = DCLogic;

  // Ленивые картинки в каруселях: подгружаем весь трек, как только он рядом с экраном,
  // иначе скрытые за overflow слайды начнут грузиться только в момент прокрутки.
  function warmTracks() {
    var tracks = document.querySelectorAll('[data-track]');
    if (!('IntersectionObserver' in window)) return;
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        io.unobserve(e.target);
        e.target.querySelectorAll('img[loading="lazy"]').forEach(function (im) { im.loading = 'eager'; });
      });
    }, { rootMargin: '400px 0px' });
    tracks.forEach(function (t) { io.observe(t); });
  }

  window.DC = {
    mount: function (Component, props) {
      var c = new Component(props);
      c.__render();
      if (c.componentDidMount) c.componentDidMount();
      warmTracks();
      return c;
    }
  };
})();
