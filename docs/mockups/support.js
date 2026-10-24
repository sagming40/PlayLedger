/*
 * docs/mockups 로컬 미리보기용 최소 런타임
 *
 * 캔버스는 자기 support.js로 .dc.html의 {{ }} · <sc-for> · <sc-if>를 풀어서 그린다.
 * 저장소 사본에는 그 파일이 없어서 브라우저로 열면 {{sc.name}} 같은 빈칸이 그대로 보였다.
 * 이 파일은 이 폴더의 목업이 쓰는 기능만 흉내 낸다 — 캔버스 런타임 전체가 아니다.
 *
 * 주소 뒤에 ?dark=false 처럼 붙이면 data-props 기본값 대신 그 값으로 그린다.
 */
(function () {
  'use strict';

  // 빈칸이 채워지기 전의 원본 마크업이 잠깐 보이지 않게 숨겨 둔다
  var hide = document.createElement('style');
  hide.textContent = 'x-dc{display:none}';
  document.head.appendChild(hide);

  // 목업의 class Component extends DCLogic가 상속받는 부모
  function DCLogic(props) {
    this.props = props || {};
    this.state = {};
  }
  DCLogic.prototype.setState = function (patch) {
    var next = typeof patch === 'function' ? patch(this.state, this.props) : patch;
    this.state = Object.assign({}, this.state, next);
    if (this.__render) this.__render();
  };
  DCLogic.prototype.forceUpdate = function () {
    if (this.__render) this.__render();
  };
  window.DCLogic = DCLogic;

  var HOLE = /\{\{\s*([^}]+?)\s*\}\}/g;

  // {{ a.b.c }} 안쪽 — 점으로 이은 경로나 리터럴만 허용한다 (캔버스 형식과 같다)
  function lookup(expr, scope) {
    expr = expr.trim();
    if (expr === 'true') return true;
    if (expr === 'false') return false;
    if (expr === 'null') return null;
    if (/^-?\d+(\.\d+)?$/.test(expr)) return Number(expr);
    if (/^(['"]).*\1$/.test(expr)) return expr.slice(1, -1);
    var parts = expr.split('.');
    var v = scope;
    for (var i = 0; i < parts.length; i++) {
      if (v == null) return undefined;
      v = v[parts[i]];
    }
    return v;
  }

  // 속성 전체가 {{ }} 하나뿐이면 그 경로를, 아니면 null
  function whole(str) {
    var m = /^\s*\{\{\s*([^}]+?)\s*\}\}\s*$/.exec(str || '');
    return m ? m[1] : null;
  }

  function interp(str, scope) {
    return str.replace(HOLE, function (_, e) {
      var v = lookup(e, scope);
      return v == null ? '' : String(v);
    });
  }

  function kids(node, scope, out) {
    for (var c = node.firstChild; c; c = c.nextSibling) {
      var rendered = render(c, scope);
      for (var i = 0; i < rendered.length; i++) out.push(rendered[i]);
    }
  }

  function render(node, scope) {
    if (node.nodeType === 3) return [document.createTextNode(interp(node.nodeValue, scope))];
    if (node.nodeType !== 1) return [];

    var tag = node.localName;
    var out = [];

    if (tag === 'helmet') return [];

    if (tag === 'sc-for') {
      var list = lookup(whole(node.getAttribute('list')) || '', scope) || [];
      var as = node.getAttribute('as') || 'item';
      list.forEach(function (item, i) {
        var s = Object.create(scope);
        s[as] = item;
        s.$index = i;
        kids(node, s, out);
      });
      return out;
    }

    if (tag === 'sc-if') {
      if (lookup(whole(node.getAttribute('value')) || 'false', scope)) kids(node, scope, out);
      return out;
    }

    // 하위 보드 — 같은 폴더의 파일을 iframe으로 띄우고 속성은 주소 뒤 값으로 넘긴다
    if (tag === 'dc-import') {
      var q = [];
      Array.prototype.forEach.call(node.attributes, function (a) {
        if (a.name === 'name' || a.name.indexOf('hint-') === 0) return;
        var w = whole(a.value);
        var v = w ? lookup(w, scope) : interp(a.value, scope);
        q.push(encodeURIComponent(a.name) + '=' + encodeURIComponent(String(v)));
      });
      var f = document.createElement('iframe');
      f.src = node.getAttribute('name') + '.dc.html' + (q.length ? '?' + q.join('&') : '');
      f.setAttribute('aria-hidden', 'true');
      f.setAttribute('tabindex', '-1');
      var size = (node.getAttribute('hint-size') || '100%,100%').split(',');
      f.style.cssText = 'display:block;border:0;width:' + size[0] + ';height:' + (size[1] || '100%');
      return [f];
    }

    var el = document.createElementNS(node.namespaceURI, tag);
    Array.prototype.forEach.call(node.attributes, function (a) {
      var name = a.name;
      if (name.indexOf('hint-') === 0) return;
      var w = whole(a.value);
      // onClick="{{ pick }}" — 파서가 onclick으로 소문자화한 것을 이벤트로 연결
      if (/^on[a-z]+$/i.test(name) && w) {
        var fn = lookup(w, scope);
        if (typeof fn === 'function') el.addEventListener(name.slice(2).toLowerCase(), fn);
        return;
      }
      if (w) {
        var v = lookup(w, scope);
        if (v === false || v == null) return;
        el.setAttribute(name, v === true ? '' : String(v));
        return;
      }
      el.setAttribute(name, interp(a.value, scope));
    });
    kids(node, scope, out);
    for (var i = 0; i < out.length; i++) el.appendChild(out[i]);
    return [el];
  }

  function parseParam(v) {
    if (v === 'true') return true;
    if (v === 'false') return false;
    if (v !== '' && !isNaN(v)) return Number(v);
    return v;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var root = document.querySelector('x-dc');
    var script = document.querySelector('script[data-dc-script]');
    if (!root || !script) return;

    var defs = {};
    try { defs = JSON.parse(script.getAttribute('data-props') || '{}'); } catch (e) { defs = {}; }
    var props = {};
    Object.keys(defs).forEach(function (k) {
      if (k.charAt(0) !== '$' && defs[k] && 'default' in defs[k]) props[k] = defs[k]['default'];
    });
    new URLSearchParams(location.search).forEach(function (v, k) { props[k] = parseParam(v); });

    var Component = new Function('DCLogic', script.textContent + '\n;return Component;')(DCLogic);
    var inst = new Component(props);

    // 원본 마크업을 틀로 떼어 두고, 그릴 때마다 이 틀에서 새로 찍어낸다
    var template = root.cloneNode(true);
    var helmet = template.querySelector('helmet');
    if (helmet) {
      Array.prototype.forEach.call(helmet.children, function (c) { document.head.appendChild(c.cloneNode(true)); });
    }

    inst.__render = function () {
      var vals = inst.renderVals ? inst.renderVals() : {};
      var out = [];
      kids(template, vals, out);
      while (root.firstChild) root.removeChild(root.firstChild);
      for (var i = 0; i < out.length; i++) root.appendChild(out[i]);
    };
    inst.__render();

    root.style.display = 'contents';
    hide.parentNode.removeChild(hide);
  });
})();
