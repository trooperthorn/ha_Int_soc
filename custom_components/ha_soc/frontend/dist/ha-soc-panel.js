function t(t,e,s,i){var a,o=arguments.length,n=o<3?e:null===i?i=Object.getOwnPropertyDescriptor(e,s):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)n=Reflect.decorate(t,e,s,i);else for(var r=t.length-1;r>=0;r--)(a=t[r])&&(n=(o<3?a(n):o>3?a(e,s,n):a(e,s))||n);return o>3&&n&&Object.defineProperty(e,s,n),n}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const e=globalThis,s=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,i=Symbol(),a=new WeakMap;let o=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==i)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(s&&void 0===t){const s=void 0!==e&&1===e.length;s&&(t=a.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&a.set(e,t))}return t}toString(){return this.cssText}};const n=(t,...e)=>{const s=1===t.length?t[0]:e.reduce((e,s,i)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+t[i+1],t[0]);return new o(s,t,i)},r=s?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const s of t.cssRules)e+=s.cssText;return(t=>new o("string"==typeof t?t:t+"",void 0,i))(e)})(t):t,{is:l,defineProperty:d,getOwnPropertyDescriptor:c,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,v=globalThis,g=v.trustedTypes,_=g?g.emptyScript:"",y=v.reactiveElementPolyfillSupport,b=(t,e)=>t,m={toAttribute(t,e){switch(e){case Boolean:t=t?_:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let s=t;switch(e){case Boolean:s=null!==t;break;case Number:s=null===t?null:Number(t);break;case Object:case Array:try{s=JSON.parse(t)}catch(t){s=null}}return s}},f=(t,e)=>!l(t,e),$={attribute:!0,type:String,converter:m,reflect:!1,useDefault:!1,hasChanged:f};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),v.litPropertyMetadata??=new WeakMap;let w=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=$){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const s=Symbol(),i=this.getPropertyDescriptor(t,s,e);void 0!==i&&d(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){const{get:i,set:a}=c(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:i,set(e){const o=i?.call(this);a?.call(this,e),this.requestUpdate(t,o,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??$}static _$Ei(){if(this.hasOwnProperty(b("elementProperties")))return;const t=u(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(b("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(b("properties"))){const t=this.properties,e=[...h(t),...p(t)];for(const s of e)this.createProperty(s,t[s])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,s]of e)this.elementProperties.set(t,s)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const s=this._$Eu(t,e);void 0!==s&&this._$Eh.set(s,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const s=new Set(t.flat(1/0).reverse());for(const t of s)e.unshift(r(t))}else void 0!==t&&e.push(r(t));return e}static _$Eu(t,e){const s=e.attribute;return!1===s?void 0:"string"==typeof s?s:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,i)=>{if(s)t.adoptedStyleSheets=i.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const s of i){const i=document.createElement("style"),a=e.litNonce;void 0!==a&&i.setAttribute("nonce",a),i.textContent=s.cssText,t.appendChild(i)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){const s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(void 0!==i&&!0===s.reflect){const a=(void 0!==s.converter?.toAttribute?s.converter:m).toAttribute(e,s.type);this._$Em=t,null==a?this.removeAttribute(i):this.setAttribute(i,a),this._$Em=null}}_$AK(t,e){const s=this.constructor,i=s._$Eh.get(t);if(void 0!==i&&this._$Em!==i){const t=s.getPropertyOptions(i),a="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:m;this._$Em=i;const o=a.fromAttribute(e,t.type);this[i]=o??this._$Ej?.get(i)??o,this._$Em=null}}requestUpdate(t,e,s,i=!1,a){if(void 0!==t){const o=this.constructor;if(!1===i&&(a=this[t]),s??=o.getPropertyOptions(t),!((s.hasChanged??f)(a,e)||s.useDefault&&s.reflect&&a===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,s))))return;this.C(t,e,s)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:a},o){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,o??e??this[t]),!0!==a||void 0!==o)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),!0===i&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,s]of t){const{wrapped:t}=s,i=this[e];!0!==t||this._$AL.has(e)||void 0===i||this.C(e,void 0,s,i)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};w.elementStyles=[],w.shadowRootOptions={mode:"open"},w[b("elementProperties")]=new Map,w[b("finalized")]=new Map,y?.({ReactiveElement:w}),(v.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const x=globalThis,k=t=>t,S=x.trustedTypes,A=S?S.createPolicy("lit-html",{createHTML:t=>t}):void 0,C="$lit$",E=`lit$${Math.random().toFixed(9).slice(2)}$`,P="?"+E,R=`<${P}>`,z=document,I=()=>z.createComment(""),U=t=>null===t||"object"!=typeof t&&"function"!=typeof t,O=Array.isArray,H="[ \t\n\f\r]",L=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,N=/-->/g,D=/>/g,F=RegExp(`>|${H}(?:([^\\s"'>=/]+)(${H}*=${H}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),T=/'/g,M=/"/g,V=/^(?:script|style|textarea|title)$/i,j=(t=>(e,...s)=>({_$litType$:t,strings:e,values:s}))(1),B=Symbol.for("lit-noChange"),q=Symbol.for("lit-nothing"),K=new WeakMap,W=z.createTreeWalker(z,129);function G(t,e){if(!O(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==A?A.createHTML(e):e}const Z=(t,e)=>{const s=t.length-1,i=[];let a,o=2===e?"<svg>":3===e?"<math>":"",n=L;for(let e=0;e<s;e++){const s=t[e];let r,l,d=-1,c=0;for(;c<s.length&&(n.lastIndex=c,l=n.exec(s),null!==l);)c=n.lastIndex,n===L?"!--"===l[1]?n=N:void 0!==l[1]?n=D:void 0!==l[2]?(V.test(l[2])&&(a=RegExp("</"+l[2],"g")),n=F):void 0!==l[3]&&(n=F):n===F?">"===l[0]?(n=a??L,d=-1):void 0===l[1]?d=-2:(d=n.lastIndex-l[2].length,r=l[1],n=void 0===l[3]?F:'"'===l[3]?M:T):n===M||n===T?n=F:n===N||n===D?n=L:(n=F,a=void 0);const h=n===F&&t[e+1].startsWith("/>")?" ":"";o+=n===L?s+R:d>=0?(i.push(r),s.slice(0,d)+C+s.slice(d)+E+h):s+E+(-2===d?e:h)}return[G(t,o+(t[s]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),i]};class J{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let a=0,o=0;const n=t.length-1,r=this.parts,[l,d]=Z(t,e);if(this.el=J.createElement(l,s),W.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(i=W.nextNode())&&r.length<n;){if(1===i.nodeType){if(i.hasAttributes())for(const t of i.getAttributeNames())if(t.endsWith(C)){const e=d[o++],s=i.getAttribute(t).split(E),n=/([.?@])?(.*)/.exec(e);r.push({type:1,index:a,name:n[2],strings:s,ctor:"."===n[1]?et:"?"===n[1]?st:"@"===n[1]?it:tt}),i.removeAttribute(t)}else t.startsWith(E)&&(r.push({type:6,index:a}),i.removeAttribute(t));if(V.test(i.tagName)){const t=i.textContent.split(E),e=t.length-1;if(e>0){i.textContent=S?S.emptyScript:"";for(let s=0;s<e;s++)i.append(t[s],I()),W.nextNode(),r.push({type:2,index:++a});i.append(t[e],I())}}}else if(8===i.nodeType)if(i.data===P)r.push({type:2,index:a});else{let t=-1;for(;-1!==(t=i.data.indexOf(E,t+1));)r.push({type:7,index:a}),t+=E.length-1}a++}}static createElement(t,e){const s=z.createElement("template");return s.innerHTML=t,s}}function Y(t,e,s=t,i){if(e===B)return e;let a=void 0!==i?s._$Co?.[i]:s._$Cl;const o=U(e)?void 0:e._$litDirective$;return a?.constructor!==o&&(a?._$AO?.(!1),void 0===o?a=void 0:(a=new o(t),a._$AT(t,s,i)),void 0!==i?(s._$Co??=[])[i]=a:s._$Cl=a),void 0!==a&&(e=Y(t,a._$AS(t,e.values),a,i)),e}class X{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??z).importNode(e,!0);W.currentNode=i;let a=W.nextNode(),o=0,n=0,r=s[0];for(;void 0!==r;){if(o===r.index){let e;2===r.type?e=new Q(a,a.nextSibling,this,t):1===r.type?e=new r.ctor(a,r.name,r.strings,this,t):6===r.type&&(e=new at(a,this,t)),this._$AV.push(e),r=s[++n]}o!==r?.index&&(a=W.nextNode(),o++)}return W.currentNode=z,i}p(t){let e=0;for(const s of this._$AV)void 0!==s&&(void 0!==s.strings?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}}class Q{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=q,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Y(this,t,e),U(t)?t===q||null==t||""===t?(this._$AH!==q&&this._$AR(),this._$AH=q):t!==this._$AH&&t!==B&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>O(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==q&&U(this._$AH)?this._$AA.nextSibling.data=t:this.T(z.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:s}=t,i="number"==typeof s?this._$AC(t):(void 0===s.el&&(s.el=J.createElement(G(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{const t=new X(i,this),s=t.u(this.options);t.p(e),this.T(s),this._$AH=t}}_$AC(t){let e=K.get(t.strings);return void 0===e&&K.set(t.strings,e=new J(t)),e}k(t){O(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let s,i=0;for(const a of t)i===e.length?e.push(s=new Q(this.O(I()),this.O(I()),this,this.options)):s=e[i],s._$AI(a),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=k(t).nextSibling;k(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class tt{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,a){this.type=1,this._$AH=q,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=a,s.length>2||""!==s[0]||""!==s[1]?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=q}_$AI(t,e=this,s,i){const a=this.strings;let o=!1;if(void 0===a)t=Y(this,t,e,0),o=!U(t)||t!==this._$AH&&t!==B,o&&(this._$AH=t);else{const i=t;let n,r;for(t=a[0],n=0;n<a.length-1;n++)r=Y(this,i[s+n],e,n),r===B&&(r=this._$AH[n]),o||=!U(r)||r!==this._$AH[n],r===q?t=q:t!==q&&(t+=(r??"")+a[n+1]),this._$AH[n]=r}o&&!i&&this.j(t)}j(t){t===q?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class et extends tt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===q?void 0:t}}class st extends tt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==q)}}class it extends tt{constructor(t,e,s,i,a){super(t,e,s,i,a),this.type=5}_$AI(t,e=this){if((t=Y(this,t,e,0)??q)===B)return;const s=this._$AH,i=t===q&&s!==q||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,a=t!==q&&(s===q||i);i&&this.element.removeEventListener(this.name,this,s),a&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class at{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){Y(this,t)}}const ot=x.litHtmlPolyfillSupport;ot?.(J,Q),(x.litHtmlVersions??=[]).push("3.3.3");const nt=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class rt extends w{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,s)=>{const i=s?.renderBefore??e;let a=i._$litPart$;if(void 0===a){const t=s?.renderBefore??null;i._$litPart$=a=new Q(e.insertBefore(I(),t),t,void 0,s??{})}return a._$AI(t),a})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return B}}rt._$litElement$=!0,rt.finalized=!0,nt.litElementHydrateSupport?.({LitElement:rt});const lt=nt.litElementPolyfillSupport;lt?.({LitElement:rt}),(nt.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const dt=t=>(e,s)=>{void 0!==s?s.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},ct={attribute:!0,type:String,converter:m,reflect:!1,hasChanged:f},ht=(t=ct,e,s)=>{const{kind:i,metadata:a}=s;let o=globalThis.litPropertyMetadata.get(a);if(void 0===o&&globalThis.litPropertyMetadata.set(a,o=new Map),"setter"===i&&((t=Object.create(t)).wrapped=!0),o.set(s.name,t),"accessor"===i){const{name:i}=s;return{set(s){const a=e.get.call(this);e.set.call(this,s),this.requestUpdate(i,a,t,!0,s)},init(e){return void 0!==e&&this.C(i,void 0,t,e),e}}}if("setter"===i){const{name:i}=s;return function(s){const a=this[i];e.call(this,s),this.requestUpdate(i,a,t,!0,s)}}throw Error("Unsupported decorator location: "+i)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function pt(t){return(e,s)=>"object"==typeof s?ht(t,e,s):((t,e,s)=>{const i=e.hasOwnProperty(s);return e.constructor.createProperty(s,t),i?Object.getOwnPropertyDescriptor(e,s):void 0})(t,e,s)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ut(t){return pt({...t,state:!0,attribute:!1})}const vt=(t,e)=>t.callWS(e),gt=t=>vt(t,{type:"ha_soc/users/list"}).then(t=>t.users),_t=t=>vt(t,{type:"ha_soc/risk/list"}).then(t=>t.risk),yt=(t,e)=>vt(t,{type:"ha_soc/detections/list",status:e}).then(t=>t.detections),bt=(t,e,s)=>vt(t,{type:"ha_soc/detections/set_status",detection_id:e,status:s}),mt=t=>vt(t,{type:"ha_soc/vulns/list"}).then(t=>t.findings),ft=t=>vt(t,{type:"ha_soc/health/list"}),$t=t=>vt(t,{type:"ha_soc/dashboard/devices"}),wt=t=>vt(t,{type:"ha_soc/dashboard/integrations"}),xt=t=>vt(t,{type:"ha_soc/probe/status"}),kt=t=>vt(t,{type:"ha_soc/peripherals/list"}),St=t=>vt(t,{type:"ha_soc/entity_remap/broken_references"}).then(t=>t.broken),At=t=>vt(t,{type:"ha_soc/security_health/list"}),Ct=n`
  :host {
    display: block;
    padding: 16px;
    max-width: 1400px;
    margin: 0 auto;

    /* Validated categorical palette (dataviz skill reference instance) —
       adjacent-pair CVD/contrast checked for chart use (bars, lines,
       stacks). Light values here; .dark overrides the dark-mode steps. */
    --cat-1: #2a78d6;
    --cat-2: #eb6834;
    --cat-3: #1baf7a;
    --cat-4: #eda100;
    --cat-5: #e87ba4;
    --cat-6: #008300;
    --cat-7: #4a3aa7;
    --cat-8: #e34948;
    --cat-other: #9aa0a6;

    /* Reserved status roles — never reused as a plain series color. */
    --status-good: #0ca30c;
    --status-warning: #fab219;
    --status-serious: #ec835a;
    --status-critical: #d03b3b;
  }
  :host(.dark) {
    --cat-1: #3987e5;
    --cat-2: #d95926;
    --cat-3: #199e70;
    --cat-4: #c98500;
    --cat-5: #d55181;
    --cat-6: #008300;
    --cat-7: #9085e9;
    --cat-8: #e66767;
    --cat-other: #7a807f;
  }
  .tabs {
    display: flex;
    gap: 4px;
    border-bottom: 1px solid var(--divider-color);
    margin-bottom: 16px;
    overflow-x: auto;
  }
  .tab {
    padding: 12px 16px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: var(--secondary-text-color);
    border-bottom: 2px solid transparent;
    white-space: nowrap;
  }
  .tab.active {
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
  }
  .card {
    background: var(--card-background-color, #fff);
    border-radius: var(--ha-card-border-radius, 12px);
    box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0, 0, 0, 0.08));
    padding: 16px;
    margin-bottom: 16px;
  }
  .card h3 {
    margin: 0 0 12px;
    font-size: 15px;
    font-weight: 600;
    color: var(--primary-text-color);
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  th,
  td {
    text-align: left;
    padding: 8px 10px;
    border-bottom: 1px solid var(--divider-color);
    vertical-align: top;
  }
  th {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--secondary-text-color);
  }
  tr:hover td {
    background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.03);
  }
  tr.row-disabled td {
    background: rgba(var(--rgb-error-color, 219, 68, 55), 0.05);
    color: var(--secondary-text-color);
  }
  tr.row-disabled td:first-child > div:first-child {
    text-decoration: line-through;
    text-decoration-color: var(--secondary-text-color);
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 100px;
    background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
  }
  .pill .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }
  .pill.critical .dot,
  .pill.high .dot {
    background: var(--error-color, #db4437);
  }
  .pill.medium .dot {
    background: var(--warning-color, #ffa600);
  }
  .pill.low .dot,
  .pill.info .dot {
    background: var(--disabled-text-color, #888);
  }
  .pill.good .dot {
    background: var(--success-color, #43a047);
  }
  .tag {
    font-size: 10.5px;
    padding: 2px 6px;
    border-radius: 5px;
    font-family: var(--code-font-family, monospace);
  }
  .tag.enforced {
    background: rgba(67, 160, 71, 0.15);
    color: var(--success-color, #43a047);
  }
  .tag.cosmetic {
    background: rgba(255, 166, 0, 0.18);
    color: var(--warning-color, #ffa600);
  }
  button.ha-btn {
    font: inherit;
    font-weight: 500;
    font-size: 13px;
    color: var(--primary-color);
    background: none;
    border: 1px solid var(--primary-color);
    border-radius: 8px;
    padding: 6px 12px;
    cursor: pointer;
  }
  button.ha-btn:hover {
    background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.08);
  }
  button.ha-btn.danger {
    color: var(--error-color, #db4437);
    border-color: var(--error-color, #db4437);
  }
  button.ha-btn:disabled {
    opacity: 0.5;
    cursor: default;
  }
  input,
  select {
    font: inherit;
    font-size: 13px;
    padding: 6px 8px;
    border-radius: 6px;
    border: 1px solid var(--divider-color);
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color);
  }
  .muted {
    color: var(--secondary-text-color);
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }
  .toolbar .spacer {
    flex: 1;
  }
  .empty {
    color: var(--secondary-text-color);
    font-size: 13px;
    padding: 24px 0;
    text-align: center;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .chip {
    font-size: 10.5px;
    background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
    padding: 2px 6px;
    border-radius: 5px;
  }
  .settings-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 10px 0;
    border-bottom: 1px solid var(--divider-color);
    font-size: 13.5px;
  }
  .settings-row:last-child {
    border-bottom: none;
  }
  .settings-row > span:first-child {
    color: var(--primary-text-color);
    flex: 1;
  }
  .settings-row input[type="number"],
  .settings-row input[type="password"],
  .settings-row input[type="text"] {
    width: 160px;
    text-align: right;
  }
  .settings-row select {
    min-width: 220px;
  }
`;let Et=class extends rt{constructor(){super(...arguments),this._users=[],this._risk={},this._loading=!0,this._busyUserId=null}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{const[t,e]=await Promise.all([gt(this.hass),_t(this.hass)]);this._users=t,this._risk=e}finally{this._loading=!1}}_fmtDate(t){if(!t)return"never";return new Date(t).toLocaleString()}async _onDeactivate(t){if(confirm("Deactivate this user? All their sessions will be revoked.")){this._busyUserId=t;try{await((t,e)=>vt(t,{type:"ha_soc/users/deactivate",user_id:e}))(this.hass,t),await this._load()}finally{this._busyUserId=null}}}async _onRevokeAll(t){if(confirm("Revoke every interactive session for this user? Long-lived tokens are kept.")){this._busyUserId=t;try{await((t,e)=>vt(t,{type:"ha_soc/users/revoke_all_sessions",user_id:e}))(this.hass,t),await this._load()}finally{this._busyUserId=null}}}async _onResetPassword(t){const e=prompt("New password for this user (owner-only action):");if(e){this._busyUserId=t;try{const s=await((t,e,s)=>vt(t,{type:"ha_soc/users/set_password",user_id:e,password:s}))(this.hass,t,e);s&&!1===s.ok&&alert("Could not set password — only the account owner can reset another user's password.")}finally{this._busyUserId=null}}}render(){return this._loading?j`<div class="empty">Loading users…</div>`:this._users.length?j`
      <div class="card">
        <h3>Users &amp; Access</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Last login is derived from refresh-token activity — a background token
          refresh looks the same as a fresh interactive login. MFA status is read
          directly from the auth store but cannot be enforced by Home Assistant.
        </p>
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Role</th>
              <th>MFA</th>
              <th>Risk</th>
              <th>Last login</th>
              <th>Tokens</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${this._users.map(t=>{const e=this._risk[t.id];return j`
                <tr class=${t.is_active?"":"row-disabled"}>
                  <td>
                    <div>${t.name??t.id}</div>
                    ${t.is_owner?j`<span class="tag enforced">owner</span>`:q}
                    ${t.is_active?q:j`<span class="tag cosmetic">deactivated</span>`}
                  </td>
                  <td>${t.is_admin?"Admin":"User"}${t.local_only?" · local only":""}</td>
                  <td>
                    ${t.mfa_enabled?j`<span class="pill good"><span class="dot"></span>enabled</span>`:j`<span class="pill high"><span class="dot"></span>none</span>`}
                  </td>
                  <td>
                    ${e?j`<span class="pill ${"critical"===e.band||"high"===e.band?"high":"moderate"===e.band?"medium":"good"}">
                          <span class="dot"></span>${e.score}
                        </span>`:j`<span class="muted">—</span>`}
                  </td>
                  <td>
                    <div>${this._fmtDate(t.last_login_at)}</div>
                    ${t.last_login_ip?j`<div class="muted">${t.last_login_ip}</div>`:q}
                  </td>
                  <td>
                    ${t.llat_count>0?j`<span class="chip">${t.llat_count} long-lived</span>`:j`<span class="muted">none</span>`}
                  </td>
                  <td>
                    <div class="toolbar" style="margin:0;">
                      <button
                        class="ha-btn"
                        ?disabled=${this._busyUserId===t.id||t.is_owner}
                        @click=${()=>this._onResetPassword(t.id)}
                      >
                        Reset password
                      </button>
                      <button
                        class="ha-btn"
                        ?disabled=${this._busyUserId===t.id}
                        @click=${()=>this._onRevokeAll(t.id)}
                      >
                        Revoke sessions
                      </button>
                      <button
                        class="ha-btn danger"
                        ?disabled=${this._busyUserId===t.id||t.is_owner}
                        @click=${()=>this._onDeactivate(t.id)}
                      >
                        Deactivate
                      </button>
                    </div>
                  </td>
                </tr>
              `})}
          </tbody>
        </table>
      </div>
    `:j`<div class="empty">No users found.</div>`}};Et.styles=Ct,t([pt({attribute:!1})],Et.prototype,"hass",void 0),t([ut()],Et.prototype,"_users",void 0),t([ut()],Et.prototype,"_risk",void 0),t([ut()],Et.prototype,"_loading",void 0),t([ut()],Et.prototype,"_busyUserId",void 0),Et=t([dt("ha-soc-users-view")],Et);const Pt=["","service_call","login_ok","login_fail","token_created","user_added","user_updated","user_removed","lovelace_change","entity_registry_change"];let Rt=class extends rt{constructor(){super(...arguments),this._events=[],this._users=[],this._loading=!0,this._category="",this._userId="",this._verifyResult=null}connectedCallback(){super.connectedCallback(),this._loadUsers(),this._load()}async _loadUsers(){this._users=await gt(this.hass)}async _load(){this._loading=!0;try{this._events=await((t,e={})=>vt(t,{type:"ha_soc/audit/query",...e}).then(t=>t.events))(this.hass,{category:this._category||void 0,user_id:this._userId||void 0,limit:200})}finally{this._loading=!1}}_nameFor(t){return t?this._users.find(e=>e.id===t)?.name??t:"—"}async _onVerify(){var t;this._verifyResult=await(t=this.hass,vt(t,{type:"ha_soc/audit/verify_chain"}))}_onCategoryChange(t){this._category=t.target.value,this._load()}_onUserChange(t){this._userId=t.target.value,this._load()}render(){return j`
      <div class="card">
        <h3>Audit Log</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Every user-attributed service call, user/dashboard change, and
          best-effort login signal. Failed logins carry only a source IP — Home
          Assistant never logs the attempted username on a failed login.
        </p>
        <div class="toolbar">
          <select @change=${this._onCategoryChange}>
            ${Pt.map(t=>j`<option value=${t} ?selected=${t===this._category}>${t||"All categories"}</option>`)}
          </select>
          <select @change=${this._onUserChange}>
            <option value="" ?selected=${""===this._userId}>All users</option>
            ${this._users.map(t=>j`<option value=${t.id} ?selected=${t.id===this._userId}>${t.name??t.id}</option>`)}
          </select>
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._onVerify}>Verify chain integrity</button>
          <button class="ha-btn" @click=${this._load}>Refresh</button>
        </div>
        ${this._verifyResult?j`<p class="${this._verifyResult.ok?"muted":""}" style="font-size:12.5px;">
              ${this._verifyResult.ok?`Chain intact — ${this._verifyResult.records_checked} records checked.`:"Chain broken — see logs for the first mismatched record."}
            </p>`:null}
        ${this._loading?j`<div class="empty">Loading…</div>`:this._events.length?j`
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Category</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._events.map(t=>j`
                      <tr>
                        <td>${new Date(t.ts).toLocaleString()}</td>
                        <td><span class="tag cosmetic">${t.category}</span></td>
                        <td>${this._nameFor(t.user_id)}</td>
                        <td>${t.domain?`${t.domain}.${t.service}`:""} ${t.entity_ids?.length?`(${t.entity_ids.join(", ")})`:""}</td>
                        <td>${t.ip??"—"}</td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:j`<div class="empty">No matching events.</div>`}
      </div>
    `}};Rt.styles=Ct,t([pt({attribute:!1})],Rt.prototype,"hass",void 0),t([ut()],Rt.prototype,"_events",void 0),t([ut()],Rt.prototype,"_users",void 0),t([ut()],Rt.prototype,"_loading",void 0),t([ut()],Rt.prototype,"_category",void 0),t([ut()],Rt.prototype,"_userId",void 0),t([ut()],Rt.prototype,"_verifyResult",void 0),Rt=t([dt("ha-soc-audit-view")],Rt);let zt=class extends rt{constructor(){super(...arguments),this._users=[],this._dashboards=[],this._selected=void 0,this._views=[],this._loading=!0,this._drift=[]}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{const[e,s]=await Promise.all([gt(this.hass),(t=this.hass,vt(t,{type:"ha_soc/permissions/dashboards/list"}).then(t=>t.dashboards))]);this._users=e.filter(t=>t.is_active),this._dashboards=s,void 0===this._selected&&s.length&&(this._selected=s[0].url_path??null),void 0!==this._selected&&await this._loadViews()}finally{this._loading=!1}var t}async _loadViews(){const t=await(e=this.hass,s=this._selected??null,vt(e,{type:"ha_soc/permissions/dashboard_config",url_path:s}).then(t=>t.config));var e,s;const i=t?.views??[];this._views=i.map((t,e)=>({path:t.path??String(e),title:t.title??t.path??`View ${e+1}`,visibleUserIds:Array.isArray(t.visible)?t.visible.map(t=>t.user):null}))}async _onSelectDashboard(t){const e=t.target.value;this._selected="__default__"===e?null:e,await this._loadViews()}async _onToggleUser(t,e){const s=t.visibleUserIds??this._users.map(t=>t.id),i=s.includes(e)?s.filter(t=>t!==e):[...s,e],a=i.length===this._users.length?[]:i;await((t,e,s,i)=>vt(t,{type:"ha_soc/permissions/view_visibility/set",url_path:e,view_path:s,user_ids:i}))(this.hass,this._selected??null,t.path,a),await this._loadViews()}async _onToggleFlag(t,e,s){await((t,e,s)=>vt(t,{type:"ha_soc/permissions/dashboard_flags/set",dashboard_id:e,...s}))(this.hass,t,{[e]:s}),await this._load()}async _onCheckDrift(){var t;this._drift=await(t=this.hass,vt(t,{type:"ha_soc/permissions/drift/check"}).then(t=>t.drift))}render(){if(this._loading)return j`<div class="empty">Loading dashboards…</div>`;const t=this._dashboards.find(t=>(t.url_path??null)===(this._selected??null));return j`
      <div class="card">
        <h3>Permissions Matrix</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag cosmetic">UI-only</span> View/card visibility and
          <code>require_admin</code> change what a user's own frontend renders — any
          authenticated user can still fetch a dashboard's full config over the
          websocket API. The only real access-control lever is a user's
          admin/non-admin group, managed in the Users &amp; Access tab.
        </p>
        <div class="toolbar">
          <select @change=${this._onSelectDashboard}>
            ${this._dashboards.map(t=>j`<option value=${t.url_path??"__default__"}>
                  ${t.title??t.url_path??"Overview"}
                </option>`)}
          </select>
          ${t?j`
                <label style="font-size:12.5px;display:flex;align-items:center;gap:4px;">
                  <input
                    type="checkbox"
                    .checked=${!!t.require_admin}
                    @change=${e=>this._onToggleFlag(t.id,"require_admin",e.target.checked)}
                  />
                  require_admin
                </label>
                <label style="font-size:12.5px;display:flex;align-items:center;gap:4px;">
                  <input
                    type="checkbox"
                    .checked=${!1!==t.show_in_sidebar}
                    @change=${e=>this._onToggleFlag(t.id,"show_in_sidebar",e.target.checked)}
                  />
                  show in sidebar
                </label>
              `:q}
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._onCheckDrift}>Check drift</button>
        </div>

        ${this._drift.length?j`<p style="font-size:12.5px;color:var(--warning-color);">
              ${this._drift.length} view(s) no longer match the policy last applied here — likely edited directly in the dashboard editor.
            </p>`:q}

        ${this._views.length?j`
              <table>
                <thead>
                  <tr>
                    <th>View</th>
                    ${this._users.map(t=>j`<th>${t.name??t.id}</th>`)}
                  </tr>
                </thead>
                <tbody>
                  ${this._views.map(t=>j`
                      <tr>
                        <td>${t.title}</td>
                        ${this._users.map(e=>{const s=null===t.visibleUserIds||t.visibleUserIds.includes(e.id);return j`
                            <td>
                              <input
                                type="checkbox"
                                .checked=${s}
                                @change=${()=>this._onToggleUser(t,e.id)}
                              />
                            </td>
                          `})}
                      </tr>
                    `)}
                </tbody>
              </table>
            `:j`<div class="empty">This dashboard has no views, or is YAML-managed (read-only).</div>`}
      </div>
    `}};zt.styles=Ct,t([pt({attribute:!1})],zt.prototype,"hass",void 0),t([ut()],zt.prototype,"_users",void 0),t([ut()],zt.prototype,"_dashboards",void 0),t([ut()],zt.prototype,"_selected",void 0),t([ut()],zt.prototype,"_views",void 0),t([ut()],zt.prototype,"_loading",void 0),t([ut()],zt.prototype,"_drift",void 0),zt=t([dt("ha-soc-permissions-view")],zt);const It=["new","confirmed","dismissed","resolved"];let Ut=class extends rt{constructor(){super(...arguments),this._scannerFindings=[],this._vulnFindings=[],this._misconfigFindings=[],this._probe=null,this._loading=!0,this._scanning=!1}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{const[e,s,i,a]=await Promise.all([(t=this.hass,vt(t,{type:"ha_soc/scanner/list"}).then(t=>t.findings)),mt(this.hass),ft(this.hass),xt(this.hass)]);this._scannerFindings=e,this._vulnFindings=s,this._misconfigFindings=i.misconfig_findings,this._probe=a}finally{this._loading=!1}var t}async _onScanIntegrations(){this._scanning=!0;try{await(t=this.hass,vt(t,{type:"ha_soc/scanner/scan_now",domain:e})),await this._load()}finally{this._scanning=!1}var t,e}async _onScanVulns(){this._scanning=!0;try{await(t=this.hass,vt(t,{type:"ha_soc/vulns/scan_now"}).then(t=>t.findings)),await this._load()}finally{this._scanning=!1}var t}async _onVulnStatus(t,e){await((t,e,s,i)=>vt(t,{type:"ha_soc/vulns/set_status",finding_id:e,status:s,note:i}))(this.hass,t,e),await this._load()}async _onMisconfigStatus(t,e){await((t,e,s,i)=>vt(t,{type:"ha_soc/misconfig/set_status",finding_id:e,status:s,note:i}))(this.hass,t,e),await this._load()}_renderStatusSelect(t,e,s){return j`
      <select @change=${t=>s(t.target.value)}>
        ${It.map(t=>j`<option value=${t} ?selected=${t===e}>${t}</option>`)}
      </select>
    `}render(){return this._loading?j`<div class="empty">Loading findings…</div>`:j`
      <div class="card">
        <h3>Misconfiguration Findings</h3>
        ${this._misconfigFindings.length?j`
              <table>
                <thead>
                  <tr>
                    <th>Check</th>
                    <th>Summary</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._misconfigFindings.map(t=>j`
                      <tr>
                        <td><span class="pill ${t.severity}"><span class="dot"></span>${t.check}</span></td>
                        <td>${t.summary}</td>
                        <td>${this._renderStatusSelect(t.id,t.status,e=>this._onMisconfigStatus(t.id,e))}</td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:j`<div class="empty">No findings.</div>`}
      </div>

      <div class="card">
        <h3>Integration Security Scanner</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Static AST/regex analysis of every installed integration's source — core and
          custom. Every finding is advisory and needs a human to confirm; Home
          Assistant's own quality tooling (hassfest) never checks for these patterns and
          never runs against custom_components at all.
        </p>
        <div class="toolbar">
          <button class="ha-btn" ?disabled=${this._scanning} @click=${this._onScanIntegrations}>
            Scan all integrations now
          </button>
        </div>
        ${this._scannerFindings.length?j`
              <table>
                <thead>
                  <tr>
                    <th>Domain</th>
                    <th>Pattern</th>
                    <th>Location</th>
                    <th>Confidence</th>
                    <th>CWE</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._scannerFindings.map(t=>j`
                      <tr>
                        <td>${t.domain}</td>
                        <td><span class="pill ${t.severity}"><span class="dot"></span>${t.pattern}</span></td>
                        <td>${t.file}:${t.line}</td>
                        <td>${t.confidence}</td>
                        <td>${t.cwe}</td>
                        <td>${this._renderStatusSelect(t.id,t.status,e=>this._onVulnStatus(t.id,e))}</td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:j`<div class="empty">No findings.</div>`}
      </div>

      <div class="card">
        <h3>Device Vulnerabilities</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Matches monitored devices against NVD by manufacturer/model — a heuristic
          match, never a confirmed exploit. Absence of a match is not evidence a device
          is secure.
        </p>
        <div class="toolbar">
          <button class="ha-btn" ?disabled=${this._scanning} @click=${this._onScanVulns}>
            Scan devices now
          </button>
        </div>
        ${this._vulnFindings.length?j`
              <table>
                <thead>
                  <tr>
                    <th>Device</th>
                    <th>CVE</th>
                    <th>CVSS</th>
                    <th>Confidence</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._vulnFindings.map(t=>j`
                      <tr>
                        <td>${t.device_name}</td>
                        <td>${t.cve_id??"—"}</td>
                        <td><span class="pill ${t.severity}"><span class="dot"></span>${t.cvss??"unscored"}</span></td>
                        <td>${t.confidence}</td>
                        <td>${this._renderStatusSelect(t.id,t.status,e=>this._onVulnStatus(t.id,e))}</td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:j`<div class="empty">No findings.</div>`}
      </div>

      ${this._renderProbeCard()}
    `}_renderProbeCard(){const t=this._probe;if(!t)return q;if(!t.supervisor)return j`
        <div class="card">
          <h3>Host Probe <span class="tag cosmetic">not available</span></h3>
          <p class="muted" style="font-size:12.5px;">
            Real socket-level port scanning of the host needs a companion add-on with
            host-network access — something a Python integration structurally cannot do
            on its own, even on Home Assistant OS. This install isn't running under
            Supervisor (Core/Container), so this feature has nothing to attach to here.
          </p>
        </div>
      `;if(!t.installed)return j`
        <div class="card">
          <h3>Host Probe <span class="tag cosmetic">not installed</span></h3>
          <p class="muted" style="font-size:12.5px;">
            The optional <strong>HA SOC Probe</strong> add-on isn't installed. It's the
            only way to see the host's actual listening ports — this integration alone
            can't reach past its own container. Add its repository under
            Settings → Add-ons → Add-on Store → ⋮ → Repositories, then install
            "HA SOC Probe". See the README for the exact URL.
          </p>
        </div>
      `;const e=t.result;return j`
      <div class="card">
        <h3>
          Host Probe
          <span class="tag ${t.running?"enforced":"cosmetic"}">
            ${t.running?"running":"installed, not running"}
          </span>
          ${t.update_available?j`<span class="tag cosmetic">update available</span>`:q}
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Version ${t.version??"unknown"}. Reports the host's real listening TCP
          ports — process-name attribution isn't included: identifying which process
          owns a port needs the add-on to also see the host's process list
          (<code>host_pid</code>), a privilege this add-on deliberately doesn't request.
        </p>
        ${e?j`
              <p class="muted" style="font-size:12px;">
                Last reported ${new Date(e.reported_at).toLocaleString()}
              </p>
              ${e.open_ports.length?j`
                    <table>
                      <thead>
                        <tr>
                          <th>Port</th>
                          <th>Protocol</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${e.open_ports.slice().sort((t,e)=>t.port-e.port).map(t=>j`
                              <tr>
                                <td>${t.port}</td>
                                <td>${t.proto}</td>
                              </tr>
                            `)}
                      </tbody>
                    </table>
                  `:j`<div class="empty">No listening ports reported.</div>`}
            `:j`<div class="empty">No scan reported yet.</div>`}
      </div>
    `}};Ut.styles=Ct,t([pt({attribute:!1})],Ut.prototype,"hass",void 0),t([ut()],Ut.prototype,"_scannerFindings",void 0),t([ut()],Ut.prototype,"_vulnFindings",void 0),t([ut()],Ut.prototype,"_misconfigFindings",void 0),t([ut()],Ut.prototype,"_probe",void 0),t([ut()],Ut.prototype,"_loading",void 0),t([ut()],Ut.prototype,"_scanning",void 0),Ut=t([dt("ha-soc-scanner-view")],Ut);function Ot(t){window.history.pushState(null,"",t),window.dispatchEvent(new CustomEvent("location-changed",{bubbles:!0,composed:!0}))}const Ht={kidde_homesafe:"Kidde HomeSafe",elkm1:"Elk-M1 Security",unifiprotect:"UniFi Protect",keymaster:"Keymaster",emporia_vue:"Emporia Vue"},Lt={lock:"Locks",siren:"Sirens",valve:"Valves"},Nt=[{key:"available",label:"Available"},{key:"partial",label:"Partial"},{key:"unavailable",label:"Unavailable"},{key:"disabled",label:"Disabled"},{key:"no_entities",label:"No Entities"}],Dt=["critical","high","medium","low"],Ft={failing:"Failing",credential:"Credential issue",communication:"Communication issue",collection:"Collection issue",errors:"Logging errors",debug_logging:"Debug logging enabled",disabled:"Disabled"},Tt=[20,50,100,"all"];let Mt=class extends rt{constructor(){super(...arguments),this._summary=null,this._deviceOverview=null,this._integrationOverview=null,this._peripherals=null,this._security=null,this._detections=[],this._risk={},this._users=[],this._loading=!0,this._deviceSearch="",this._deviceStatusFilter=null,this._deviceSort={key:"risk_score",dir:"desc"},this._devicePageSize=20}connectedCallback(){super.connectedCallback(),this._load()}updated(){this.classList.toggle("dark",!!this.hass?.themes?.darkMode)}async _load(){this._loading=!0;try{const[e,s,i,a,o,n,r,l]=await Promise.all([(t=this.hass,vt(t,{type:"ha_soc/dashboard/summary"})),$t(this.hass),wt(this.hass),kt(this.hass),At(this.hass),yt(this.hass),_t(this.hass),gt(this.hass)]);this._summary=e,this._deviceOverview=s,this._integrationOverview=i,this._peripherals=a,this._security=o,this._detections=n,this._risk=r,this._users=l}finally{this._loading=!1}var t}async _onAck(t){await bt(this.hass,t,"ack"),await this._load()}async _onResolve(t){await bt(this.hass,t,"resolved"),await this._load()}_nameFor(t){return t?this._users.find(e=>e.id===t)?.name??t:"unknown"}_goto(t){!function(t,e){t.dispatchEvent(new CustomEvent("ha-soc-navigate",{detail:{tab:e},bubbles:!0,composed:!0}))}(this,t)}_donutGradient(t){const e=t.reduce((t,e)=>t+e.value,0)||1;let s=0;const i=t.map(t=>{const i=s/e*100;s+=t.value;const a=s/e*100;return`${t.color} ${i}% ${a}%`});return`conic-gradient(${i.join(", ")})`}_onSort(t){this._deviceSort=this._deviceSort.key===t?{key:t,dir:"asc"===this._deviceSort.dir?"desc":"asc"}:{key:t,dir:"name"===t||"vendor"===t?"asc":"desc"}}_onStatusTileClick(t){this._deviceStatusFilter=this._deviceStatusFilter===t?null:t,this.renderRoot.querySelector("#devices-card")?.scrollIntoView({behavior:"smooth",block:"start"})}_sortedFilteredDevices(){const t=this._deviceOverview?.devices??[],e=this._deviceSearch.trim().toLowerCase(),s=t.filter(t=>(!this._deviceStatusFilter||t.status===this._deviceStatusFilter)&&(!e||(t.name.toLowerCase().includes(e)||t.vendor.toLowerCase().includes(e)||t.os.toLowerCase().includes(e)))),{key:i,dir:a}=this._deviceSort,o=[...s].sort((t,e)=>{const s=t[i],o=e[i],n="string"==typeof s?s.localeCompare(o):s-o;return"asc"===a?n:-n});return o}_statusDotColor(t){switch(t){case"unavailable":return"var(--status-critical)";case"partial":return"var(--status-warning)";case"disabled":return"var(--cat-other)";case"no_entities":return"var(--primary-color)";default:return"var(--status-good)"}}_issueCategoryColor(t){switch(t){case"failing":return"var(--status-critical)";case"credential":return"var(--cat-7)";case"communication":return"var(--status-serious)";case"collection":return"var(--status-warning)";case"errors":return"var(--cat-5)";case"debug_logging":return"var(--cat-1)";default:return"var(--cat-other)"}}render(){if(this._loading||!this._summary||!this._deviceOverview||!this._integrationOverview)return j`<div class="empty">Loading dashboard…</div>`;const t=this._summary,e=this._deviceOverview,s=this._integrationOverview,i=this._detections.filter(t=>"open"===t.status),a=e.devices.reduce((t,e)=>(t.critical+=e.severity_counts.critical,t.high+=e.severity_counts.high,t.medium+=e.severity_counts.medium,t.low+=e.severity_counts.low,t),{critical:0,high:0,medium:0,low:0}),o=a.critical+a.high+a.medium+a.low,n=[{key:"critical",label:"Critical",color:"var(--status-critical)",value:a.critical},{key:"high",label:"High",color:"var(--status-serious)",value:a.high},{key:"medium",label:"Medium",color:"var(--status-warning)",value:a.medium},{key:"low",label:"Low",color:"var(--status-good)",value:a.low}],r=Math.max(0,Math.min(100,e.combined_risk_score/10*100)),l=t.entity_state_counts??{unavailable:0,unknown:0},d=l.unavailable+l.unknown,c=[{key:"unavailable",label:"Failed (unavailable)",color:"var(--status-critical)",value:l.unavailable},{key:"unknown",label:"Unknown",color:"var(--status-warning)",value:l.unknown}],h=this._sortedFilteredDevices(),p="all"===this._devicePageSize?h:h.slice(0,this._devicePageSize),u=[{key:"low",color:"var(--status-good)",value:t.risk_band_counts.low??0},{key:"moderate",color:"var(--status-warning)",value:t.risk_band_counts.moderate??0},{key:"high",color:"var(--status-serious)",value:t.risk_band_counts.high??0},{key:"critical",color:"var(--status-critical)",value:t.risk_band_counts.critical??0}],v=[{key:"enabled",color:"var(--cat-1)",value:t.mfa_counts.enabled},{key:"disabled",color:"var(--cat-2)",value:t.mfa_counts.disabled}],g=[{key:"critical",color:"var(--status-critical)",value:t.detection_severity_counts.critical??0},{key:"high",color:"var(--status-serious)",value:t.detection_severity_counts.high??0},{key:"medium",color:"var(--status-warning)",value:t.detection_severity_counts.medium??0},{key:"low",color:"var(--status-good)",value:t.detection_severity_counts.low??0}];return j`
      ${this._renderSecurityCard()}

      <h2 class="section-title">Device &amp; Vulnerability Overview</h2>
      <div class="row3">
        <div class="card device-status-card">
          <h3>Device Status</h3>
          <div class="status-tiles">
            ${Nt.map(t=>j`
                <div
                  class="status-tile clickable ${t.key} ${this._deviceStatusFilter===t.key?"active":""}"
                  title="Filter the devices table below"
                  @click=${()=>this._onStatusTileClick(t.key)}
                >
                  <div class="label">${t.label}</div>
                  <div class="value">${e.status_counts[t.key]??0}</div>
                </div>
              `)}
          </div>
        </div>

        <div class="card clickable" @click=${()=>this._goto("scanner")} title="View vulnerability findings">
          <h3>Vulnerability Count by Severity</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(n)}">
              <div class="center">${o.toLocaleString()}</div>
            </div>
            <div class="legend">
              ${n.map(t=>j`
                  <div class="row">
                    <span class="sw" style="background:${t.color}"></span>${t.label}
                    <span class="val">${t.value.toLocaleString()}</span>
                  </div>
                `)}
            </div>
          </div>
        </div>

        <div class="card gauge-card clickable" @click=${()=>this._goto("scanner")} title="View vulnerability findings">
          <h3>Risk Score</h3>
          <div class="gauge-value">${e.combined_risk_score.toFixed(1)}</div>
          <div class="gauge-track">
            <div class="gauge-marker" style="left:${r}%"></div>
          </div>
          <div class="gauge-caption">
            Combined risk score of all devices — weighted so higher-severity CVEs count more.
          </div>
        </div>

        <div class="card clickable" @click=${()=>this._goto("entity_remap")} title="Fix broken entity references">
          <h3>Failed / Unknown Entities</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(c)}">
              <div class="center">${d.toLocaleString()}</div>
            </div>
            <div class="legend">
              ${c.map(t=>j`
                  <div class="row">
                    <span class="sw" style="background:${t.color}"></span>${t.label}
                    <span class="val">${t.value.toLocaleString()}</span>
                  </div>
                `)}
            </div>
          </div>
        </div>
      </div>

      <h2 class="section-title">Users &amp; Detections</h2>
      <div class="donuts-row">
        <div class="card clickable" @click=${()=>this._goto("users")} title="View users">
          <h3>Users by Risk Band</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(u)}">
              <div class="center">${t.total_users_count}</div>
            </div>
            <div class="legend">
              ${u.map(t=>j`
                  <div class="row">
                    <span class="sw" style="background:${t.color}"></span>${t.key}
                    <span class="val">${t.value}</span>
                  </div>
                `)}
            </div>
          </div>
        </div>

        <div class="card clickable" @click=${()=>this._goto("users")} title="View users">
          <h3>MFA Adoption</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(v)}">
              <div class="center">
                ${t.mfa_counts.enabled+t.mfa_counts.disabled>0?`${Math.round(t.mfa_counts.enabled/(t.mfa_counts.enabled+t.mfa_counts.disabled)*100)}%`:"—"}
              </div>
            </div>
            <div class="legend">
              <div class="row"><span class="sw" style="background:var(--cat-1)"></span>Enabled<span class="val">${t.mfa_counts.enabled}</span></div>
              <div class="row"><span class="sw" style="background:var(--cat-2)"></span>No MFA<span class="val">${t.mfa_counts.disabled}</span></div>
            </div>
          </div>
        </div>

        <div class="card clickable" @click=${()=>this._goto("audit")} title="View audit / detections">
          <h3>Detections by Severity</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(g)}">
              <div class="center">${this._detections.length}</div>
            </div>
            <div class="legend">
              ${g.map(t=>j`
                  <div class="row">
                    <span class="sw" style="background:${t.color}"></span>${t.key}
                    <span class="val">${t.value}</span>
                  </div>
                `)}
            </div>
          </div>
        </div>
      </div>

      ${this._renderPeripheralsCard()}

      <div class="card">
        <h3>Recent suspicious activity</h3>
        ${i.length?j`
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Rule</th>
                    <th>Severity</th>
                    <th>User</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${i.map(t=>j`
                      <tr>
                        <td>${new Date(t.last_seen).toLocaleString()}</td>
                        <td>${t.title}</td>
                        <td><span class="pill ${t.severity}"><span class="dot"></span>${t.severity}</span></td>
                        <td>${this._nameFor(t.user_id)}</td>
                        <td>
                          <button class="ha-btn" @click=${()=>this._onAck(t.id)}>Ack</button>
                          <button class="ha-btn" @click=${()=>this._onResolve(t.id)}>Resolve</button>
                        </td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:j`<div class="empty">No open detections.</div>`}
      </div>

      <h2 class="section-title">Devices &amp; Integrations</h2>
      <div class="row2">
        <div class="card" id="devices-card">
          <h3>All Devices</h3>
          ${this._deviceStatusFilter?j`
                <div class="filter-chip" @click=${()=>this._deviceStatusFilter=null}>
                  ${Nt.find(t=>t.key===this._deviceStatusFilter)?.label} ✕
                </div>
              `:q}
          <div class="devices-toolbar">
            <input
              type="text"
              placeholder="Search devices…"
              .value=${this._deviceSearch}
              @input=${t=>this._deviceSearch=t.target.value}
            />
          </div>
          ${0===h.length?j`<div class="empty">No devices found.</div>`:j`
                <div style="overflow-x:auto;">
                  <table>
                    <thead>
                      <tr>
                        <th>Health</th>
                        <th class="sortable" @click=${()=>this._onSort("name")}>
                          Device${this._sortArrow("name")}
                        </th>
                        <th class="sortable" @click=${()=>this._onSort("vendor")}>
                          Vendor${this._sortArrow("vendor")}
                        </th>
                        <th class="sortable" @click=${()=>this._onSort("risk_score")}>
                          Risk Score${this._sortArrow("risk_score")}
                        </th>
                        <th class="sortable" @click=${()=>this._onSort("total_findings")}>
                          Total${this._sortArrow("total_findings")}
                        </th>
                        <th>Severity</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${p.map(t=>j`
                          <tr
                            class="clickable"
                            title="Open in Home Assistant's Devices page"
                            @click=${()=>Ot(`/config/devices/device/${t.device_id}`)}
                          >
                            <td><span class="health-dot" style="background:${this._statusDotColor(t.status)}"></span></td>
                            <td>${t.name}</td>
                            <td class="muted">${t.vendor}</td>
                            <td class="num">${t.risk_score.toFixed(1)}</td>
                            <td class="num">${t.total_findings}</td>
                            <td>
                              <span class="sev-cell">
                                ${Dt.map(e=>j`
                                    <span>
                                      <span
                                        class="sev-dot"
                                        style="background:${"critical"===e?"var(--status-critical)":"high"===e?"var(--status-serious)":"medium"===e?"var(--status-warning)":"var(--status-good)"}"
                                      ></span
                                      >${t.severity_counts[e]}
                                    </span>
                                  `)}
                              </span>
                            </td>
                          </tr>
                        `)}
                    </tbody>
                  </table>
                </div>
                <div class="devices-footer">
                  <span
                    >Showing ${p.length} of ${h.length} device${1===h.length?"":"s"}</span
                  >
                  <select
                    .value=${String(this._devicePageSize)}
                    @change=${t=>{const e=t.target.value;this._devicePageSize="all"===e?"all":Number(e)}}
                  >
                    ${Tt.map(t=>j`
                        <option value=${String(t)} ?selected=${t===this._devicePageSize}>
                          ${"all"===t?"Show all":`Show ${t}`}
                        </option>
                      `)}
                  </select>
                </div>
              `}
        </div>

        <div class="card">
          <h3>Issues by Integration</h3>
          ${0===s.integrations.length?j`<div class="empty">No integration issues detected.</div>`:j`
                <div class="issues-list">
                  ${s.integrations.map(t=>j`
                      <div
                        class="issues-row clickable"
                        title="${t.title} — ${Ft[t.issue_category]}. Open in Home Assistant's Devices page"
                        @click=${()=>Ot(`/config/devices/dashboard?historyBack=1&config_entry=${t.entry_id}`)}
                      >
                        <span class="issues-dot" style="background:${this._issueCategoryColor(t.issue_category)}"></span>
                        <span class="issues-name">${t.title}</span>
                        <span class="issues-category muted">${Ft[t.issue_category]}</span>
                        <span class="issues-count">${t.error_count_24h}</span>
                      </div>
                    `)}
                </div>
              `}
        </div>
      </div>
    `}_sortArrow(t){return this._deviceSort.key!==t?q:j`<span class="arrow">${"asc"===this._deviceSort.dir?"▲":"▼"}</span>`}_renderSecurityCard(){const t=this._security;if(!t)return q;const e={};for(const s of t.entities)(e[s.domain]??=[]).push(s);return j`
      <div class="card">
        <h3>
          Security Integrations Health
          ${t.problem_count||t.low_battery_count?j`<span class="tag" style="background:rgba(219,68,55,0.15);color:var(--error-color,#db4437);">
                ${t.problem_count} problem${1===t.problem_count?"":"s"}, ${t.low_battery_count} low
                battery
              </span>`:j`<span class="tag enforced">all clear</span>`}
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Every lock/siren/valve entity regardless of integration, plus config-entry health
          for a curated set of security-relevant integrations. Configurable in Settings.
        </p>
        <div class="security-health-grid">
          ${Object.entries(Lt).filter(([e])=>t.sources_enabled[e]??!0).map(([t,s])=>{const i=e[t]??[],a=i.filter(t=>t.problem).length,o=i.filter(t=>t.low_battery).length;return j`
                <div class="security-source-tile">
                  <div class="label">${s}</div>
                  <div class="value" style="color:${a?"var(--error-color,#db4437)":"inherit"}">
                    ${i.length}
                  </div>
                  <div class="sub">
                    ${a?`${a} problem${1===a?"":"s"}`:"none reporting a problem"}${o?`, ${o} low battery`:""}
                  </div>
                </div>
              `})}
          ${Object.entries(Ht).filter(([e])=>t.sources_enabled[e]??!0).map(([e,s])=>{const i=t.integrations.filter(t=>t.domain===e),a=i.some(t=>t.installed),o=i.some(t=>t.installed&&"loaded"!==t.state);return j`
                <div class="security-source-tile">
                  <div class="label">${s}</div>
                  <div
                    class="value"
                    style="font-size:14px;color:${o?"var(--error-color,#db4437)":"inherit"};"
                  >
                    ${a?o?i.find(t=>"loaded"!==t.state).state:"loaded":"not installed"}
                  </div>
                </div>
              `})}
        </div>
      </div>
    `}_renderPeripheralsCard(){const t=this._peripherals;return t&&t.available?j`
      <div class="card clickable" @click=${()=>this._goto("peripherals")} title="View Local Peripherals">
        <h3>Local Peripherals</h3>
        ${t.total_count?j`
              <div class="peripherals-stats">
                <div>
                  <div class="peripherals-stat-value">${t.total_count}</div>
                  <div class="muted">Serial device${1===t.total_count?"":"s"} detected</div>
                </div>
                <div>
                  <div class="peripherals-stat-value" style="color:${t.unassigned_count?"var(--status-warning)":"inherit"}">
                    ${t.unassigned_count}
                  </div>
                  <div class="muted">Unassigned</div>
                </div>
              </div>
            `:j`<div class="empty">No USB serial devices detected.</div>`}
      </div>
    `:q}};function Vt(t){const e=t.match(/^homeassistant\.components\.([^.]+)/);if(e)return e[1];const s=t.match(/^custom_components\.([^.]+)/);return s?s[1]:t.split(".")[0]}Mt.styles=[Ct,n`
      h2.section-title {
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--secondary-text-color);
        margin: 28px 0 12px;
        font-weight: 600;
      }
      h2.section-title:first-child {
        margin-top: 0;
      }

      .row3 {
        display: grid;
        grid-template-columns: 1.3fr 1fr 1fr 1fr;
        gap: 12px;
        margin-bottom: 16px;
      }
      .row2 {
        display: grid;
        grid-template-columns: 1.4fr 1fr;
        gap: 12px;
        margin-bottom: 16px;
      }
      .donuts-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 16px;
      }
      @media (max-width: 900px) {
        .row3,
        .row2,
        .donuts-row {
          grid-template-columns: 1fr;
        }
      }

      .clickable {
        cursor: pointer;
        transition: transform 0.08s ease, box-shadow 0.08s ease;
      }
      .clickable:hover {
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12);
        transform: translateY(-1px);
      }

      /* -- Status tiles -------------------------------------------------- */
      /* Stretches to fill whatever height row3's tallest sibling card
         (the donut / gauge cards) ends up at, rather than sizing to its
         own short content and leaving dead space below. */
      .device-status-card {
        display: flex;
        flex-direction: column;
      }
      .status-tiles {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        flex: 1;
      }
      .status-tile {
        border-radius: 10px;
        padding: 10px 6px;
        text-align: center;
        background: var(--card-background-color, #fff);
        border: 1px solid var(--divider-color);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 6px;
      }
      .status-tile.active {
        outline: 2px solid var(--primary-color);
        outline-offset: -2px;
      }
      .status-tile .label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        opacity: 0.85;
      }
      .status-tile .value {
        font-size: 26px;
        font-weight: 700;
        line-height: 1.3;
      }
      .status-tile.partial {
        background: var(--status-warning);
        color: #3a2900;
      }
      .status-tile.unavailable {
        background: var(--status-critical);
        color: #fff;
      }
      .status-tile.disabled {
        background: var(--cat-other);
        color: #fff;
      }
      .status-tile.no_entities {
        background: var(--primary-color);
        color: #fff;
      }

      .filter-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        background: var(--primary-color);
        color: #fff;
        padding: 4px 10px;
        border-radius: 100px;
        cursor: pointer;
        margin-bottom: 10px;
      }

      /* -- Donut ----------------------------------------------------------- */
      .donut-wrap {
        display: flex;
        align-items: center;
        gap: 14px;
      }
      .donut {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        position: relative;
        flex: none;
      }
      .donut::after {
        content: "";
        position: absolute;
        inset: 22%;
        border-radius: 50%;
        background: var(--card-background-color, #fff);
      }
      .donut .center {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 18px;
        z-index: 1;
      }
      .legend {
        font-size: 12px;
        display: flex;
        flex-direction: column;
        gap: 6px;
        flex: 1;
        min-width: 0;
      }
      .legend .row {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .legend .sw {
        width: 9px;
        height: 9px;
        border-radius: 2px;
        flex: none;
      }
      .legend .val {
        margin-left: auto;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
      }

      /* -- Risk gauge ------------------------------------------------------ */
      .gauge-card .gauge-value {
        font-size: 30px;
        font-weight: 700;
        margin-bottom: 10px;
      }
      .gauge-track {
        position: relative;
        height: 12px;
        border-radius: 6px;
        background: linear-gradient(
          90deg,
          var(--status-good) 0%,
          var(--status-warning) 40%,
          var(--status-serious) 70%,
          var(--status-critical) 100%
        );
      }
      .gauge-marker {
        position: absolute;
        top: -10px;
        width: 0;
        height: 0;
        border-left: 7px solid transparent;
        border-right: 7px solid transparent;
        border-top: 9px solid var(--primary-text-color);
        transform: translateX(-50%);
      }
      .gauge-caption {
        margin-top: 10px;
        font-size: 11.5px;
        color: var(--secondary-text-color);
      }

      /* -- All Devices table --------------------------------------------------- */
      .devices-toolbar {
        display: flex;
        gap: 8px;
        margin-bottom: 10px;
      }
      .devices-toolbar input {
        flex: 1;
        font: inherit;
        font-size: 13px;
        padding: 7px 10px;
        border-radius: 8px;
        border: 1px solid var(--divider-color);
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color);
      }
      th.sortable {
        cursor: pointer;
        user-select: none;
      }
      th.sortable .arrow {
        opacity: 0.6;
        margin-left: 3px;
      }
      .health-dot {
        display: inline-block;
        width: 9px;
        height: 9px;
        border-radius: 50%;
      }
      .sev-cell {
        display: inline-flex;
        gap: 8px;
        font-variant-numeric: tabular-nums;
        font-size: 11.5px;
      }
      .sev-cell span {
        display: inline-flex;
        align-items: center;
        gap: 3px;
      }
      .sev-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
      }

      /* -- Issues by Integration (list) ---------------------------------- */
      .issues-list {
        display: flex;
        flex-direction: column;
        max-height: 340px;
        overflow-y: auto;
      }
      .issues-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 4px;
        border-bottom: 1px solid var(--divider-color);
        font-size: 13px;
      }
      .issues-row:last-child {
        border-bottom: none;
      }
      .issues-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        flex: none;
      }
      .issues-name {
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .issues-category {
        font-size: 11px;
        flex: none;
      }
      .issues-count {
        font-weight: 700;
        font-variant-numeric: tabular-nums;
        flex: none;
        min-width: 20px;
        text-align: right;
      }

      /* -- All Devices pagination ------------------------------------------ */
      .devices-footer {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 10px;
        font-size: 12.5px;
        color: var(--secondary-text-color);
      }
      .devices-footer select {
        margin-left: auto;
      }

      /* -- Local Peripherals summary card ---------------------------------- */
      .peripherals-stats {
        display: flex;
        gap: 32px;
      }
      .peripherals-stat-value {
        font-size: 26px;
        font-weight: 700;
        line-height: 1.3;
      }

      /* -- Security Integrations Health card --------------------------------- */
      .security-health-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-top: 8px;
      }
      .security-source-tile {
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        padding: 10px 12px;
      }
      .security-source-tile .label {
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-bottom: 4px;
      }
      .security-source-tile .value {
        font-size: 20px;
        font-weight: 700;
      }
      .security-source-tile .sub {
        font-size: 11px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
    `],t([pt({attribute:!1})],Mt.prototype,"hass",void 0),t([ut()],Mt.prototype,"_summary",void 0),t([ut()],Mt.prototype,"_deviceOverview",void 0),t([ut()],Mt.prototype,"_integrationOverview",void 0),t([ut()],Mt.prototype,"_peripherals",void 0),t([ut()],Mt.prototype,"_security",void 0),t([ut()],Mt.prototype,"_detections",void 0),t([ut()],Mt.prototype,"_risk",void 0),t([ut()],Mt.prototype,"_users",void 0),t([ut()],Mt.prototype,"_loading",void 0),t([ut()],Mt.prototype,"_deviceSearch",void 0),t([ut()],Mt.prototype,"_deviceStatusFilter",void 0),t([ut()],Mt.prototype,"_deviceSort",void 0),t([ut()],Mt.prototype,"_devicePageSize",void 0),Mt=t([dt("ha-soc-dashboard-view")],Mt);let jt=class extends rt{constructor(){super(...arguments),this._entries=[],this._loading=!0,this._domainFilter="",this._expanded=new Set}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{this._entries=await(t=this.hass,vt(t,{type:"system_log/list"}))}finally{this._loading=!1}var t}_toggleExpanded(t){const e=new Set(this._expanded);e.has(t)?e.delete(t):e.add(t),this._expanded=e}get _domains(){return Array.from(new Set(this._entries.map(t=>Vt(t.name)))).sort()}get _filtered(){return this._domainFilter?this._entries.filter(t=>Vt(t.name)===this._domainFilter):this._entries}render(){const t=this._filtered;return j`
      <div class="card">
        <h3>Home Assistant Logs</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          The same WARNING/ERROR/CRITICAL buffer as Settings → System → Logs
          (<code>/config/logs</code>) — deduplicated, most recent first. This shows Home
          Assistant's own captured log records only;
          <strong>add-on container logs aren't included</strong> — they're a separate
          stream Supervisor captures per-container, not part of Home Assistant's Python
          logging, so there's nothing for this view to filter. Check an add-on's own
          Log tab (Settings → Add-ons → the add-on → Log) for those.
        </p>
        <div class="toolbar">
          <select @change=${t=>this._domainFilter=t.target.value}>
            <option value="" ?selected=${""===this._domainFilter}>All integrations</option>
            ${this._domains.map(t=>j`<option value=${t} ?selected=${t===this._domainFilter}>${t}</option>`)}
          </select>
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._load}>Refresh</button>
        </div>
        ${this._loading?j`<div class="empty">Loading…</div>`:t.length?j`
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Level</th>
                    <th>Integration</th>
                    <th>Message</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  ${t.map((t,e)=>{const s=this._expanded.has(e);return j`
                      <tr
                        class=${t.exception?"clickable":""}
                        title=${t.exception?"Click to show/hide the traceback":""}
                        @click=${()=>t.exception&&this._toggleExpanded(e)}
                      >
                        <td>${new Date(1e3*t.first_occurred).toLocaleString()}</td>
                        <td>
                          <span class="pill ${function(t){switch(t){case"CRITICAL":return"critical";case"ERROR":return"high";case"WARNING":return"medium";default:return"low"}}(t.level)}"
                            ><span class="dot"></span>${t.level}</span
                          >
                        </td>
                        <td class="muted">${Vt(t.name)}</td>
                        <td>
                          ${t.message[t.message.length-1]}
                          ${t.source?j`<div class="muted" style="font-size:11px;">${t.source[0]}:${t.source[1]}</div>`:q}
                        </td>
                        <td class="num">${t.count}</td>
                      </tr>
                      ${s&&t.exception?j`
                            <tr>
                              <td colspan="5">
                                <pre
                                  style="white-space:pre-wrap;font-size:11.5px;background:rgba(var(--rgb-primary-text-color,0,0,0),0.04);padding:10px;border-radius:6px;margin:0;"
                                >
${t.exception}</pre
                                >
                              </td>
                            </tr>
                          `:q}
                    `})}
                </tbody>
              </table>
            `:j`<div class="empty">No matching log entries.</div>`}
      </div>
    `}};jt.styles=Ct,t([pt({attribute:!1})],jt.prototype,"hass",void 0),t([ut()],jt.prototype,"_entries",void 0),t([ut()],jt.prototype,"_loading",void 0),t([ut()],jt.prototype,"_domainFilter",void 0),t([ut()],jt.prototype,"_expanded",void 0),jt=t([dt("ha-soc-logs-view")],jt);let Bt=class extends rt{constructor(){super(...arguments),this._overview=null,this._loading=!0,this._busyKey=null,this._showIgnored=!1}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{this._overview=await kt(this.hass)}finally{this._loading=!1}}async _onToggleIgnore(t,e,s){this._busyKey=t;try{await((t,e,s,i)=>vt(t,{type:"ha_soc/peripherals/set_ignored",key:e,ignored:s,raw_name:i}))(this.hass,t,e,s),await this._load()}finally{this._busyKey=null}}render(){if(this._loading)return j`<div class="empty">Loading peripherals…</div>`;const t=this._overview;if(!t||!t.available)return j`
        <div class="card">
          <h3>Local Peripherals</h3>
          <p class="muted" style="font-size:12.5px;">
            Home Assistant's own USB discovery component (<code>usb</code>) isn't
            available — it's part of every default install, so this usually only
            happens if it's been explicitly disabled. This view has nothing to read
            without it.
          </p>
        </div>
      `;const e=t.devices.filter(t=>!t.ignored),s=t.devices.filter(t=>t.ignored);return j`
      <div class="card">
        <h3>Local Peripherals</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          USB serial devices Home Assistant itself can see — the same discovery data
          core uses to auto-detect a Zigbee/Z-Wave USB stick, so no add-on is involved.
          This only covers serial (<code>/dev/ttyUSB*</code>/<code>/dev/ttyACM*</code>)
          devices, not every USB peripheral. "Assigned integration" is a best-effort
          match against every config entry's stored data — a miss doesn't prove a
          device is unused, only that this couldn't find it.
        </p>
        ${t.devices.length?j`
              <table>
                <thead>
                  <tr>
                    <th>Raw Name</th>
                    <th>/dev/tty Path</th>
                    <th>Assigned Integration</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${e.map(t=>j`
                      <tr>
                        <td>${t.raw_name}</td>
                        <td class="muted">${t.tty_path}</td>
                        <td>
                          ${t.assigned_integration?j`${t.assigned_integration.title}
                                <span class="muted">(${t.assigned_integration.domain})</span>`:j`<span class="pill medium"><span class="dot"></span>unassigned</span>`}
                        </td>
                        <td>
                          ${t.assigned_integration?q:j`
                                <button
                                  class="ha-btn"
                                  ?disabled=${this._busyKey===t.key}
                                  @click=${()=>this._onToggleIgnore(t.key,!0,t.raw_name)}
                                >
                                  Ignore
                                </button>
                              `}
                        </td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:j`<div class="empty">
              No USB serial devices detected. If you're expecting one here, confirm
              Home Assistant actually has access to it — automatic on Home Assistant
              OS for devices your system exposes; a Container/Core install needs the
              device passed through explicitly (e.g. Docker's <code>--device</code>).
            </div>`}
      </div>

      ${s.length?j`
            <div class="card">
              <h3 style="cursor:pointer;" @click=${()=>this._showIgnored=!this._showIgnored}>
                Ignored (${s.length}) ${this._showIgnored?"▲":"▼"}
              </h3>
              ${this._showIgnored?j`
                    <table>
                      <thead>
                        <tr>
                          <th>Raw Name</th>
                          <th>/dev/tty Path</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        ${s.map(t=>j`
                            <tr class="row-disabled">
                              <td>${t.raw_name}</td>
                              <td class="muted">${t.tty_path}</td>
                              <td>
                                <button
                                  class="ha-btn"
                                  ?disabled=${this._busyKey===t.key}
                                  @click=${()=>this._onToggleIgnore(t.key,!1,t.raw_name)}
                                >
                                  Un-ignore
                                </button>
                              </td>
                            </tr>
                          `)}
                      </tbody>
                    </table>
                  `:q}
            </div>
          `:q}
    `}};Bt.styles=Ct,t([pt({attribute:!1})],Bt.prototype,"hass",void 0),t([ut()],Bt.prototype,"_overview",void 0),t([ut()],Bt.prototype,"_loading",void 0),t([ut()],Bt.prototype,"_busyKey",void 0),t([ut()],Bt.prototype,"_showIgnored",void 0),Bt=t([dt("ha-soc-peripherals-view")],Bt);const qt={automation:"Automations",script:"Scripts",scene:"Scenes",dashboard:"Views (dashboards)",helper:"Helpers",other:"Other (review manually)"};let Kt=class extends rt{constructor(){super(...arguments),this._entities=[],this._oldEntityId="",this._newEntityId="",this._report=null,this._finding=!1,this._applying=!1,this._applyResult=null,this._broken=[],this._brokenLoading=!0}connectedCallback(){super.connectedCallback(),this._load()}async _load(){const[t,e]=await Promise.all([(s=this.hass,vt(s,{type:"config/entity_registry/list"})),St(this.hass)]);var s;this._entities=t,this._broken=e,this._brokenLoading=!1}_labelFor(t){const e=this._entities.find(e=>e.entity_id===t),s=e?.name||e?.original_name;return s?`${s} (${t})`:t}async _onFind(){if(this._oldEntityId){this._finding=!0,this._applyResult=null;try{this._report=await(t=this.hass,e=this._oldEntityId,vt(t,{type:"ha_soc/entity_remap/find_references",entity_id:e}))}finally{this._finding=!1}var t,e}}_onFixBroken(t){this._oldEntityId=t,this._newEntityId="",this._report=null,this._applyResult=null,this._onFind()}async _onApply(){if(this._oldEntityId&&this._newEntityId){this._applying=!0;try{const i=await(t=this.hass,e=this._oldEntityId,s=this._newEntityId,vt(t,{type:"ha_soc/entity_remap/apply",old_entity_id:e,new_entity_id:s}));await this._onFind(),this._broken=await St(this.hass),this._applyResult=i}finally{this._applying=!1}var t,e,s}}_renderKind(t,e){return e.length?j`
      <div style="margin-bottom:12px;">
        <div style="font-size:12px;font-weight:600;color:var(--secondary-text-color);margin-bottom:4px;">
          ${qt[t]??t} (${e.length})
        </div>
        <table>
          <tbody>
            ${e.map(t=>j`
                <tr>
                  <td>${t.name}</td>
                  <td>
                    <span class="tag ${t.editable?"enforced":"cosmetic"}">
                      ${t.editable?"will fix":"manual review"}
                    </span>
                  </td>
                  <td class="muted" style="font-size:12px;">${t.reason??""}</td>
                </tr>
              `)}
          </tbody>
        </table>
      </div>
    `:q}render(){const t=this._report,e=!!t&&t.editable_count>0&&!!this._newEntityId&&this._newEntityId!==this._oldEntityId;return j`
      <div class="card">
        <h3>Entity ReMap</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Home Assistant has no built-in way to do this: renaming or replacing an entity
          only ever touches the entity registry — every automation, script, scene,
          dashboard, and helper that still references the old entity_id keeps that exact
          string and silently breaks. Pick the broken/old entity and its replacement below
          to find every reference and fix the ones that are safely, structurally editable.
          A reference that only exists inside a template (<code>{{ states('...') }}</code>)
          is never rewritten automatically — it's flagged for you to fix by hand instead,
          since a text rewrite there risks corrupting the template or missing a dynamic
          reference.
        </p>

        <div class="toolbar" style="align-items:flex-end;">
          <div>
            <div class="muted" style="font-size:11px;margin-bottom:2px;">Old / broken entity</div>
            <input
              list="ha-soc-remap-entities"
              style="width:320px;"
              .value=${this._oldEntityId}
              placeholder="sensor.old_entity_id"
              @change=${t=>this._oldEntityId=t.target.value.trim()}
            />
          </div>
          <div>
            <div class="muted" style="font-size:11px;margin-bottom:2px;">New / replacement entity</div>
            <input
              list="ha-soc-remap-entities"
              style="width:320px;"
              .value=${this._newEntityId}
              placeholder="sensor.new_entity_id"
              @change=${t=>this._newEntityId=t.target.value.trim()}
            />
          </div>
          <button class="ha-btn" ?disabled=${!this._oldEntityId||this._finding} @click=${()=>this._onFind()}>
            ${this._finding?"Searching…":"Find references"}
          </button>
          <datalist id="ha-soc-remap-entities">
            ${this._entities.map(t=>j`<option value=${t.entity_id}>${t.name??t.original_name??""}</option>`)}
          </datalist>
        </div>

        ${t?j`
              <div style="margin-top:12px;">
                ${0===t.total_count?j`<div class="empty">No references to ${t.entity_id} found anywhere.</div>`:j`
                      <p class="muted" style="font-size:12.5px;">
                        ${t.total_count} reference(s) found — ${t.editable_count} can be fixed
                        automatically, the rest need a manual look.
                      </p>
                      ${this._renderKind("automation",t.automation)}
                      ${this._renderKind("script",t.script)}
                      ${this._renderKind("scene",t.scene)}
                      ${this._renderKind("dashboard",t.dashboard)}
                      ${this._renderKind("helper",t.helper)}
                      ${this._renderKind("other",t.other)}
                    `}
                <button class="ha-btn" ?disabled=${!e||this._applying} @click=${()=>this._onApply()}>
                  ${this._applying?"Applying…":`Apply remap (${t.editable_count} reference${1===t.editable_count?"":"s"})`}
                </button>
              </div>
            `:q}

        ${this._applyResult?j`
              <div class="card" style="margin-top:12px;background:rgba(67,160,71,0.08);">
                <strong>Applied.</strong> ${Object.entries(this._applyResult.fixed).filter(([,t])=>t>0).map(([t,e])=>`${e} ${qt[t]??t}`).join(", ")||"Nothing needed changing."}
                ${this._applyResult.errors.length?j`<div style="color:var(--error-color);margin-top:6px;">
                      ${this._applyResult.errors.length} error(s): ${this._applyResult.errors.join("; ")}
                    </div>`:q}
              </div>
            `:q}
      </div>

      <div class="card">
        <h3>Entities referenced but not found (${this._broken.length})</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          A proactive sweep of every automation, script, scene, and structured helper —
          any entity_id they reference that doesn't correspond to a known entity right now.
          Dashboards aren't swept here (there's no equivalent core-provided index to walk
          cheaply); use the search above for a specific entity_id to also cover those.
        </p>
        ${this._brokenLoading?j`<div class="empty">Loading…</div>`:this._broken.length?j`
                <table>
                  <thead>
                    <tr>
                      <th>Entity ID</th>
                      <th>Referenced by</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    ${this._broken.map(t=>j`
                        <tr>
                          <td><code>${t.entity_id}</code></td>
                          <td class="muted" style="font-size:12px;">
                            ${t.referenced_by.map(t=>`${t.name} (${t.kind})`).join(", ")}
                          </td>
                          <td>
                            <button class="ha-btn" @click=${()=>this._onFixBroken(t.entity_id)}>Fix…</button>
                          </td>
                        </tr>
                      `)}
                  </tbody>
                </table>
              `:j`<div class="empty">Nothing found — no dangling entity references detected.</div>`}
      </div>
    `}};Kt.styles=Ct,t([pt({attribute:!1})],Kt.prototype,"hass",void 0),t([ut()],Kt.prototype,"_entities",void 0),t([ut()],Kt.prototype,"_oldEntityId",void 0),t([ut()],Kt.prototype,"_newEntityId",void 0),t([ut()],Kt.prototype,"_report",void 0),t([ut()],Kt.prototype,"_finding",void 0),t([ut()],Kt.prototype,"_applying",void 0),t([ut()],Kt.prototype,"_applyResult",void 0),t([ut()],Kt.prototype,"_broken",void 0),t([ut()],Kt.prototype,"_brokenLoading",void 0),Kt=t([dt("ha-soc-entity-remap-view")],Kt);const Wt=1048576,Gt=[{domain:"lock",label:"Lock entities (any integration)"},{domain:"siren",label:"Siren entities (any integration)"},{domain:"valve",label:"Valve entities (any integration)"},{domain:"kidde_homesafe",label:"Kidde HomeSafe"},{domain:"elkm1",label:"Elk-M1 Security"},{domain:"unifiprotect",label:"UniFi Protect"},{domain:"keymaster",label:"Keymaster"},{domain:"emporia_vue",label:"Emporia Vue"}];let Zt=class extends rt{constructor(){super(...arguments),this._settings=null,this._loading=!0}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{this._settings=await(t=this.hass,vt(t,{type:"ha_soc/settings/get"}))}finally{this._loading=!1}var t}async _update(t,e){if(!this._settings)return;const s=this._settings;this._settings={...this._settings,[t]:e};try{this._settings=await(i=this.hass,a={[t]:e},vt(i,{type:"ha_soc/settings/set",...a}))}catch(t){throw this._settings=s,t}var i,a}_updateSecuritySource(t,e){this._settings&&this._update("security_sources_enabled",{...this._settings.security_sources_enabled,[t]:e})}render(){if(this._loading||!this._settings)return j`<div class="empty">Loading settings…</div>`;const t=this._settings;return j`
      <div class="card">
        <h3>Access Control</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag enforced">enforced</span> Checked server-side on every
          <code>ha_soc/*</code> command, not just on whether the panel is visible in the
          sidebar — a locked-out admin still sees the SOC panel entry (Home Assistant's
          sidebar has no finer-grained hook than admin/non-admin) but every request it
          makes is rejected until this is opened up.
        </p>
        <label class="settings-row">
          <span>Who can use this panel</span>
          <select
            .value=${t.access_level}
            @change=${t=>this._update("access_level",t.target.value)}
          >
            <option value="owner_only">Account owner only</option>
            <option value="owner_and_admins">Owner and all administrators</option>
          </select>
        </label>
      </div>

      <div class="card">
        <h3>MFA Non-Compliance Policy</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Home Assistant core has no hook to <em>require</em> a second factor at login —
          this can only ever <span class="tag cosmetic">audit</span> that gap, or take the
          one real action core does expose:
          <span class="tag enforced">enforced</span> deactivating an admin account that
          stays out of compliance past the grace period below. The account owner is never
          evaluated or deactivated by this policy.
        </p>
        <label class="settings-row">
          <span>Policy for admins without MFA enabled</span>
          <select
            .value=${t.mfa_policy}
            @change=${t=>this._update("mfa_policy",t.target.value)}
          >
            <option value="audit_only">Audit only — flag via Repairs, never act</option>
            <option value="auto_deactivate">Deactivate after grace period</option>
          </select>
        </label>
        <label class="settings-row">
          <span>Grace period (days)</span>
          <input
            type="number"
            min="1"
            max="365"
            .value=${String(t.mfa_grace_period_days)}
            ?disabled=${"auto_deactivate"!==t.mfa_policy}
            @change=${t=>this._update("mfa_grace_period_days",Number(t.target.value))}
          />
        </label>
      </div>

      <div class="card">
        <h3>Device Vulnerability Scanning</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag cosmetic">best-effort</span> CVE correlation is a heuristic
          vendor/model match against NVD, not a confirmed exploit — absence of a match is
          not evidence a device is secure.
        </p>
        <label class="settings-row">
          <span>NVD API key (optional — raises the public rate limit)</span>
          <input
            type="password"
            placeholder="unset"
            .value=${t.nvd_api_key??""}
            @change=${t=>this._update("nvd_api_key",t.target.value||null)}
          />
        </label>
        <label class="settings-row">
          <span>Risk-scoring learning period (days)</span>
          <input
            type="number"
            min="1"
            max="90"
            .value=${String(t.risk_learning_period_days)}
            @change=${t=>this._update("risk_learning_period_days",Number(t.target.value))}
          />
        </label>
      </div>

      <div class="card">
        <h3>Integration Security Scanner</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Static analysis of every installed integration's source, run on the weekly
          sweep below or on demand from the Scanner tab.
        </p>
        <label class="settings-row">
          <span>Run the weekly scan automatically</span>
          <input
            type="checkbox"
            .checked=${t.scanner_enabled}
            @change=${t=>this._update("scanner_enabled",t.target.checked)}
          />
        </label>
        <label class="settings-row">
          <span>
            Include network-reachability checks
            <span class="muted" style="display:block;font-size:11.5px;"
              >Best-effort connectivity probes against configured device hosts — off by
              default since it makes outbound requests.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${t.scanner_network_checks_enabled}
            @change=${t=>this._update("scanner_network_checks_enabled",t.target.checked)}
          />
        </label>
      </div>

      <div class="card">
        <h3>Audit Log</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag enforced">enforced</span> Hash-chained JSONL, rotated on
          whichever of these two limits is hit first — see the Audit Log tab's
          <code>Verify chain</code> action.
        </p>
        <label class="settings-row">
          <span>Retention (days)</span>
          <input
            type="number"
            min="7"
            max="3650"
            .value=${String(t.audit_retention_days)}
            @change=${t=>this._update("audit_retention_days",Number(t.target.value))}
          />
        </label>
        <label class="settings-row">
          <span>Maximum size (MB)</span>
          <input
            type="number"
            min="1"
            .value=${String(Math.round(t.audit_max_bytes/Wt))}
            @change=${t=>this._update("audit_max_bytes",Math.round(Number(t.target.value)*Wt))}
          />
        </label>
      </div>

      <div class="card">
        <h3>Security Integrations Health</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          What shows up in the always-present Dashboard security card. A source stays on
          by default — a device or integration you haven't installed just reports "not
          installed" rather than being hidden, and turning a toggle off here only affects
          this dashboard section, nothing else.
        </p>
        ${Gt.map(({domain:e,label:s})=>j`
            <label class="settings-row">
              <span>${s}</span>
              <input
                type="checkbox"
                .checked=${t.security_sources_enabled[e]??!0}
                @change=${t=>this._updateSecuritySource(e,t.target.checked)}
              />
            </label>
          `)}
      </div>

      <div class="card">
        <h3>Host Probe Add-on</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Real socket-level port visibility on the Home Assistant host needs the optional
          <strong>HA SOC Probe</strong> companion add-on — see the Scanner tab's Host
          Probe card for its current status, and the project README for install steps.
          Nothing to configure here; the add-on's own scan interval is set from its own
          add-on Configuration tab.
        </p>
      </div>
    `}};Zt.styles=Ct,t([pt({attribute:!1})],Zt.prototype,"hass",void 0),t([ut()],Zt.prototype,"_settings",void 0),t([ut()],Zt.prototype,"_loading",void 0),Zt=t([dt("ha-soc-settings-view")],Zt);const Jt=[{id:"dashboard",label:"Dashboard"},{id:"entity_remap",label:"Entity ReMap"},{id:"users",label:"Users & Access"},{id:"permissions",label:"Permissions"},{id:"audit",label:"Audit Log"},{id:"peripherals",label:"Local Peripherals"},{id:"scanner",label:"Scanner"},{id:"logs",label:"Logs"},{id:"settings",label:"Settings"}];let Yt=class extends rt{constructor(){super(...arguments),this._tab="dashboard",this._access=null}connectedCallback(){super.connectedCallback(),this._loadAccess()}async _loadAccess(){try{this._access=await(t=this.hass,vt(t,{type:"ha_soc/access/info"}))}catch{this._access={is_owner:!1,access_level:"owner_only",allowed:!1}}var t}render(){return null===this._access?j`<div class="header">🛡️ HA SOC</div>`:this._access.allowed?j`
      <div class="header">🛡️ HA SOC</div>
      <div class="tabs">
        ${Jt.map(t=>j`
            <div class="tab ${this._tab===t.id?"active":""}" @click=${()=>this._tab=t.id}>
              ${t.label}
            </div>
          `)}
      </div>
      <div @ha-soc-navigate=${this._onNavigate}>${this._renderTab()}</div>
    `:j`
        <div class="denied">
          <div class="icon">🛡️🚫</div>
          <h2>Access restricted</h2>
          <p>
            HA SOC is currently set to <strong>account owner only</strong>. Your account
            is an administrator, but not the account owner, so this panel and its data
            aren't reachable from here.
          </p>
          <p>
            The owner can open this up to every administrator from
            <strong>Settings → Devices &amp; Services → HA SOC → Configure</strong>, or
            from this panel's own Settings tab once they've signed in.
          </p>
        </div>
      `}_onNavigate(t){this._tab=t.detail.tab}_renderTab(){switch(this._tab){case"users":return j`<ha-soc-users-view .hass=${this.hass}></ha-soc-users-view>`;case"audit":return j`<ha-soc-audit-view .hass=${this.hass}></ha-soc-audit-view>`;case"permissions":return j`<ha-soc-permissions-view .hass=${this.hass}></ha-soc-permissions-view>`;case"scanner":return j`<ha-soc-scanner-view .hass=${this.hass}></ha-soc-scanner-view>`;case"logs":return j`<ha-soc-logs-view .hass=${this.hass}></ha-soc-logs-view>`;case"peripherals":return j`<ha-soc-peripherals-view .hass=${this.hass}></ha-soc-peripherals-view>`;case"entity_remap":return j`<ha-soc-entity-remap-view .hass=${this.hass}></ha-soc-entity-remap-view>`;case"settings":return j`<ha-soc-settings-view .hass=${this.hass}></ha-soc-settings-view>`;default:return j`<ha-soc-dashboard-view .hass=${this.hass}></ha-soc-dashboard-view>`}}};Yt.styles=n`
    :host {
      display: block;
      background: var(--primary-background-color);
      min-height: 100vh;
    }
    .tabs {
      display: flex;
      gap: 4px;
      border-bottom: 1px solid var(--divider-color);
      padding: 0 16px;
      background: var(--card-background-color, #fff);
      overflow-x: auto;
    }
    .tab {
      padding: 14px 16px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      color: var(--secondary-text-color);
      border-bottom: 2px solid transparent;
      white-space: nowrap;
    }
    .tab.active {
      color: var(--primary-color);
      border-bottom-color: var(--primary-color);
    }
    .header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px 0;
      font-size: 20px;
      font-weight: 500;
      color: var(--primary-text-color);
    }
    .denied {
      max-width: 480px;
      margin: 15vh auto 0;
      padding: 32px;
      text-align: center;
      color: var(--primary-text-color);
    }
    .denied .icon {
      font-size: 40px;
    }
    .denied h2 {
      margin: 12px 0 4px;
      font-size: 18px;
    }
    .denied p {
      color: var(--secondary-text-color);
      font-size: 13.5px;
      line-height: 1.5;
    }
  `,t([pt({attribute:!1})],Yt.prototype,"hass",void 0),t([pt({attribute:!1})],Yt.prototype,"narrow",void 0),t([pt({attribute:!1})],Yt.prototype,"panel",void 0),t([ut()],Yt.prototype,"_tab",void 0),t([ut()],Yt.prototype,"_access",void 0),Yt=t([dt("ha-soc-panel")],Yt);export{Yt as HaSocPanel};
