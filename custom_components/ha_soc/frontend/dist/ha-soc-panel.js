function t(t,e,s,i){var o,a=arguments.length,r=a<3?e:null===i?i=Object.getOwnPropertyDescriptor(e,s):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)r=Reflect.decorate(t,e,s,i);else for(var n=t.length-1;n>=0;n--)(o=t[n])&&(r=(a<3?o(r):a>3?o(e,s,r):o(e,s))||r);return a>3&&r&&Object.defineProperty(e,s,r),r}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const e=globalThis,s=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,i=Symbol(),o=new WeakMap;let a=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==i)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(s&&void 0===t){const s=void 0!==e&&1===e.length;s&&(t=o.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&o.set(e,t))}return t}toString(){return this.cssText}};const r=(t,...e)=>{const s=1===t.length?t[0]:e.reduce((e,s,i)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+t[i+1],t[0]);return new a(s,t,i)},n=s?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const s of t.cssRules)e+=s.cssText;return(t=>new a("string"==typeof t?t:t+"",void 0,i))(e)})(t):t,{is:d,defineProperty:l,getOwnPropertyDescriptor:c,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,_=globalThis,v=_.trustedTypes,g=v?v.emptyScript:"",y=_.reactiveElementPolyfillSupport,b=(t,e)=>t,f={toAttribute(t,e){switch(e){case Boolean:t=t?g:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let s=t;switch(e){case Boolean:s=null!==t;break;case Number:s=null===t?null:Number(t);break;case Object:case Array:try{s=JSON.parse(t)}catch(t){s=null}}return s}},m=(t,e)=>!d(t,e),$={attribute:!0,type:String,converter:f,reflect:!1,useDefault:!1,hasChanged:m};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),_.litPropertyMetadata??=new WeakMap;let w=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=$){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const s=Symbol(),i=this.getPropertyDescriptor(t,s,e);void 0!==i&&l(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){const{get:i,set:o}=c(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:i,set(e){const a=i?.call(this);o?.call(this,e),this.requestUpdate(t,a,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??$}static _$Ei(){if(this.hasOwnProperty(b("elementProperties")))return;const t=u(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(b("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(b("properties"))){const t=this.properties,e=[...h(t),...p(t)];for(const s of e)this.createProperty(s,t[s])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,s]of e)this.elementProperties.set(t,s)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const s=this._$Eu(t,e);void 0!==s&&this._$Eh.set(s,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const s=new Set(t.flat(1/0).reverse());for(const t of s)e.unshift(n(t))}else void 0!==t&&e.push(n(t));return e}static _$Eu(t,e){const s=e.attribute;return!1===s?void 0:"string"==typeof s?s:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,i)=>{if(s)t.adoptedStyleSheets=i.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const s of i){const i=document.createElement("style"),o=e.litNonce;void 0!==o&&i.setAttribute("nonce",o),i.textContent=s.cssText,t.appendChild(i)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){const s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(void 0!==i&&!0===s.reflect){const o=(void 0!==s.converter?.toAttribute?s.converter:f).toAttribute(e,s.type);this._$Em=t,null==o?this.removeAttribute(i):this.setAttribute(i,o),this._$Em=null}}_$AK(t,e){const s=this.constructor,i=s._$Eh.get(t);if(void 0!==i&&this._$Em!==i){const t=s.getPropertyOptions(i),o="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:f;this._$Em=i;const a=o.fromAttribute(e,t.type);this[i]=a??this._$Ej?.get(i)??a,this._$Em=null}}requestUpdate(t,e,s,i=!1,o){if(void 0!==t){const a=this.constructor;if(!1===i&&(o=this[t]),s??=a.getPropertyOptions(t),!((s.hasChanged??m)(o,e)||s.useDefault&&s.reflect&&o===this._$Ej?.get(t)&&!this.hasAttribute(a._$Eu(t,s))))return;this.C(t,e,s)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:o},a){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,a??e??this[t]),!0!==o||void 0!==a)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),!0===i&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,s]of t){const{wrapped:t}=s,i=this[e];!0!==t||this._$AL.has(e)||void 0===i||this.C(e,void 0,s,i)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};w.elementStyles=[],w.shadowRootOptions={mode:"open"},w[b("elementProperties")]=new Map,w[b("finalized")]=new Map,y?.({ReactiveElement:w}),(_.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const x=globalThis,A=t=>t,k=x.trustedTypes,S=k?k.createPolicy("lit-html",{createHTML:t=>t}):void 0,E="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,U="?"+C,P=`<${U}>`,R=document,O=()=>R.createComment(""),T=t=>null===t||"object"!=typeof t&&"function"!=typeof t,M=Array.isArray,z="[ \t\n\f\r]",N=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,H=/-->/g,D=/>/g,I=RegExp(`>|${z}(?:([^\\s"'>=/]+)(${z}*=${z}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),L=/'/g,F=/"/g,V=/^(?:script|style|textarea|title)$/i,j=(t=>(e,...s)=>({_$litType$:t,strings:e,values:s}))(1),q=Symbol.for("lit-noChange"),B=Symbol.for("lit-nothing"),W=new WeakMap,G=R.createTreeWalker(R,129);function J(t,e){if(!M(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==S?S.createHTML(e):e}const K=(t,e)=>{const s=t.length-1,i=[];let o,a=2===e?"<svg>":3===e?"<math>":"",r=N;for(let e=0;e<s;e++){const s=t[e];let n,d,l=-1,c=0;for(;c<s.length&&(r.lastIndex=c,d=r.exec(s),null!==d);)c=r.lastIndex,r===N?"!--"===d[1]?r=H:void 0!==d[1]?r=D:void 0!==d[2]?(V.test(d[2])&&(o=RegExp("</"+d[2],"g")),r=I):void 0!==d[3]&&(r=I):r===I?">"===d[0]?(r=o??N,l=-1):void 0===d[1]?l=-2:(l=r.lastIndex-d[2].length,n=d[1],r=void 0===d[3]?I:'"'===d[3]?F:L):r===F||r===L?r=I:r===H||r===D?r=N:(r=I,o=void 0);const h=r===I&&t[e+1].startsWith("/>")?" ":"";a+=r===N?s+P:l>=0?(i.push(n),s.slice(0,l)+E+s.slice(l)+C+h):s+C+(-2===l?e:h)}return[J(t,a+(t[s]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),i]};class Z{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let o=0,a=0;const r=t.length-1,n=this.parts,[d,l]=K(t,e);if(this.el=Z.createElement(d,s),G.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(i=G.nextNode())&&n.length<r;){if(1===i.nodeType){if(i.hasAttributes())for(const t of i.getAttributeNames())if(t.endsWith(E)){const e=l[a++],s=i.getAttribute(t).split(C),r=/([.?@])?(.*)/.exec(e);n.push({type:1,index:o,name:r[2],strings:s,ctor:"."===r[1]?et:"?"===r[1]?st:"@"===r[1]?it:tt}),i.removeAttribute(t)}else t.startsWith(C)&&(n.push({type:6,index:o}),i.removeAttribute(t));if(V.test(i.tagName)){const t=i.textContent.split(C),e=t.length-1;if(e>0){i.textContent=k?k.emptyScript:"";for(let s=0;s<e;s++)i.append(t[s],O()),G.nextNode(),n.push({type:2,index:++o});i.append(t[e],O())}}}else if(8===i.nodeType)if(i.data===U)n.push({type:2,index:o});else{let t=-1;for(;-1!==(t=i.data.indexOf(C,t+1));)n.push({type:7,index:o}),t+=C.length-1}o++}}static createElement(t,e){const s=R.createElement("template");return s.innerHTML=t,s}}function Y(t,e,s=t,i){if(e===q)return e;let o=void 0!==i?s._$Co?.[i]:s._$Cl;const a=T(e)?void 0:e._$litDirective$;return o?.constructor!==a&&(o?._$AO?.(!1),void 0===a?o=void 0:(o=new a(t),o._$AT(t,s,i)),void 0!==i?(s._$Co??=[])[i]=o:s._$Cl=o),void 0!==o&&(e=Y(t,o._$AS(t,e.values),o,i)),e}class Q{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??R).importNode(e,!0);G.currentNode=i;let o=G.nextNode(),a=0,r=0,n=s[0];for(;void 0!==n;){if(a===n.index){let e;2===n.type?e=new X(o,o.nextSibling,this,t):1===n.type?e=new n.ctor(o,n.name,n.strings,this,t):6===n.type&&(e=new ot(o,this,t)),this._$AV.push(e),n=s[++r]}a!==n?.index&&(o=G.nextNode(),a++)}return G.currentNode=R,i}p(t){let e=0;for(const s of this._$AV)void 0!==s&&(void 0!==s.strings?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}}class X{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=B,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Y(this,t,e),T(t)?t===B||null==t||""===t?(this._$AH!==B&&this._$AR(),this._$AH=B):t!==this._$AH&&t!==q&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>M(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==B&&T(this._$AH)?this._$AA.nextSibling.data=t:this.T(R.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:s}=t,i="number"==typeof s?this._$AC(t):(void 0===s.el&&(s.el=Z.createElement(J(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{const t=new Q(i,this),s=t.u(this.options);t.p(e),this.T(s),this._$AH=t}}_$AC(t){let e=W.get(t.strings);return void 0===e&&W.set(t.strings,e=new Z(t)),e}k(t){M(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let s,i=0;for(const o of t)i===e.length?e.push(s=new X(this.O(O()),this.O(O()),this,this.options)):s=e[i],s._$AI(o),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=A(t).nextSibling;A(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class tt{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,o){this.type=1,this._$AH=B,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=o,s.length>2||""!==s[0]||""!==s[1]?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=B}_$AI(t,e=this,s,i){const o=this.strings;let a=!1;if(void 0===o)t=Y(this,t,e,0),a=!T(t)||t!==this._$AH&&t!==q,a&&(this._$AH=t);else{const i=t;let r,n;for(t=o[0],r=0;r<o.length-1;r++)n=Y(this,i[s+r],e,r),n===q&&(n=this._$AH[r]),a||=!T(n)||n!==this._$AH[r],n===B?t=B:t!==B&&(t+=(n??"")+o[r+1]),this._$AH[r]=n}a&&!i&&this.j(t)}j(t){t===B?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class et extends tt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===B?void 0:t}}class st extends tt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==B)}}class it extends tt{constructor(t,e,s,i,o){super(t,e,s,i,o),this.type=5}_$AI(t,e=this){if((t=Y(this,t,e,0)??B)===q)return;const s=this._$AH,i=t===B&&s!==B||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,o=t!==B&&(s===B||i);i&&this.element.removeEventListener(this.name,this,s),o&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class ot{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){Y(this,t)}}const at=x.litHtmlPolyfillSupport;at?.(Z,X),(x.litHtmlVersions??=[]).push("3.3.3");const rt=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class nt extends w{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,s)=>{const i=s?.renderBefore??e;let o=i._$litPart$;if(void 0===o){const t=s?.renderBefore??null;i._$litPart$=o=new X(e.insertBefore(O(),t),t,void 0,s??{})}return o._$AI(t),o})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return q}}nt._$litElement$=!0,nt.finalized=!0,rt.litElementHydrateSupport?.({LitElement:nt});const dt=rt.litElementPolyfillSupport;dt?.({LitElement:nt}),(rt.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const lt=t=>(e,s)=>{void 0!==s?s.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},ct={attribute:!0,type:String,converter:f,reflect:!1,hasChanged:m},ht=(t=ct,e,s)=>{const{kind:i,metadata:o}=s;let a=globalThis.litPropertyMetadata.get(o);if(void 0===a&&globalThis.litPropertyMetadata.set(o,a=new Map),"setter"===i&&((t=Object.create(t)).wrapped=!0),a.set(s.name,t),"accessor"===i){const{name:i}=s;return{set(s){const o=e.get.call(this);e.set.call(this,s),this.requestUpdate(i,o,t,!0,s)},init(e){return void 0!==e&&this.C(i,void 0,t,e),e}}}if("setter"===i){const{name:i}=s;return function(s){const o=this[i];e.call(this,s),this.requestUpdate(i,o,t,!0,s)}}throw Error("Unsupported decorator location: "+i)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function pt(t){return(e,s)=>"object"==typeof s?ht(t,e,s):((t,e,s)=>{const i=e.hasOwnProperty(s);return e.constructor.createProperty(s,t),i?Object.getOwnPropertyDescriptor(e,s):void 0})(t,e,s)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ut(t){return pt({...t,state:!0,attribute:!1})}const _t=r`
  :host {
    display: block;
    padding: 16px;
    max-width: 1400px;
    margin: 0 auto;
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
`,vt=(t,e)=>t.callWS(e),gt=t=>vt(t,{type:"ha_soc/users/list"}).then(t=>t.users),yt=t=>vt(t,{type:"ha_soc/risk/list"}).then(t=>t.risk),bt=(t,e)=>vt(t,{type:"ha_soc/detections/list",status:e}).then(t=>t.detections),ft=(t,e,s)=>vt(t,{type:"ha_soc/detections/set_status",detection_id:e,status:s}),mt=t=>vt(t,{type:"ha_soc/vulns/list"}).then(t=>t.findings),$t=t=>vt(t,{type:"ha_soc/health/list"});let wt=class extends nt{constructor(){super(...arguments),this._users=[],this._risk={},this._loading=!0,this._busyUserId=null}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{const[t,e]=await Promise.all([gt(this.hass),yt(this.hass)]);this._users=t,this._risk=e}finally{this._loading=!1}}_fmtDate(t){if(!t)return"never";return new Date(t).toLocaleString()}async _onDeactivate(t){if(confirm("Deactivate this user? All their sessions will be revoked.")){this._busyUserId=t;try{await((t,e)=>vt(t,{type:"ha_soc/users/deactivate",user_id:e}))(this.hass,t),await this._load()}finally{this._busyUserId=null}}}async _onRevokeAll(t){if(confirm("Revoke every interactive session for this user? Long-lived tokens are kept.")){this._busyUserId=t;try{await((t,e)=>vt(t,{type:"ha_soc/users/revoke_all_sessions",user_id:e}))(this.hass,t),await this._load()}finally{this._busyUserId=null}}}async _onResetPassword(t){const e=prompt("New password for this user (owner-only action):");if(e){this._busyUserId=t;try{const s=await((t,e,s)=>vt(t,{type:"ha_soc/users/set_password",user_id:e,password:s}))(this.hass,t,e);s&&!1===s.ok&&alert("Could not set password — only the account owner can reset another user's password.")}finally{this._busyUserId=null}}}render(){return this._loading?j`<div class="empty">Loading users…</div>`:this._users.length?j`
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
                <tr>
                  <td>
                    <div>${t.name??t.id}</div>
                    ${t.is_owner?j`<span class="tag enforced">owner</span>`:B}
                    ${t.is_active?B:j`<span class="tag cosmetic">disabled</span>`}
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
                    ${t.last_login_ip?j`<div class="muted">${t.last_login_ip}</div>`:B}
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
    `:j`<div class="empty">No users found.</div>`}};wt.styles=_t,t([pt({attribute:!1})],wt.prototype,"hass",void 0),t([ut()],wt.prototype,"_users",void 0),t([ut()],wt.prototype,"_risk",void 0),t([ut()],wt.prototype,"_loading",void 0),t([ut()],wt.prototype,"_busyUserId",void 0),wt=t([lt("ha-soc-users-view")],wt);const xt=["","service_call","login_ok","login_fail","token_created","user_added","user_updated","user_removed","lovelace_change","entity_registry_change"];let At=class extends nt{constructor(){super(...arguments),this._events=[],this._loading=!0,this._category="",this._verifyResult=null}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{this._events=await((t,e={})=>vt(t,{type:"ha_soc/audit/query",...e}).then(t=>t.events))(this.hass,{category:this._category||void 0,limit:200})}finally{this._loading=!1}}async _onVerify(){var t;this._verifyResult=await(t=this.hass,vt(t,{type:"ha_soc/audit/verify_chain"}))}_onCategoryChange(t){this._category=t.target.value,this._load()}render(){return j`
      <div class="card">
        <h3>Audit Log</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Every user-attributed service call, user/dashboard change, and
          best-effort login signal. Failed logins carry only a source IP — Home
          Assistant never logs the attempted username on a failed login.
        </p>
        <div class="toolbar">
          <select @change=${this._onCategoryChange}>
            ${xt.map(t=>j`<option value=${t} ?selected=${t===this._category}>${t||"All categories"}</option>`)}
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
                        <td>${t.user_id??"—"}</td>
                        <td>${t.domain?`${t.domain}.${t.service}`:""} ${t.entity_ids?.length?`(${t.entity_ids.join(", ")})`:""}</td>
                        <td>${t.ip??"—"}</td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:j`<div class="empty">No matching events.</div>`}
      </div>
    `}};At.styles=_t,t([pt({attribute:!1})],At.prototype,"hass",void 0),t([ut()],At.prototype,"_events",void 0),t([ut()],At.prototype,"_loading",void 0),t([ut()],At.prototype,"_category",void 0),t([ut()],At.prototype,"_verifyResult",void 0),At=t([lt("ha-soc-audit-view")],At);let kt=class extends nt{constructor(){super(...arguments),this._users=[],this._dashboards=[],this._selected=void 0,this._views=[],this._loading=!0,this._drift=[]}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{const[e,s]=await Promise.all([gt(this.hass),(t=this.hass,vt(t,{type:"ha_soc/permissions/dashboards/list"}).then(t=>t.dashboards))]);this._users=e.filter(t=>t.is_active),this._dashboards=s,void 0===this._selected&&s.length&&(this._selected=s[0].url_path??null),void 0!==this._selected&&await this._loadViews()}finally{this._loading=!1}var t}async _loadViews(){const t=await(e=this.hass,s=this._selected??null,vt(e,{type:"ha_soc/permissions/dashboard_config",url_path:s}).then(t=>t.config));var e,s;const i=t?.views??[];this._views=i.map((t,e)=>({path:t.path??String(e),title:t.title??t.path??`View ${e+1}`,visibleUserIds:Array.isArray(t.visible)?t.visible.map(t=>t.user):null}))}async _onSelectDashboard(t){const e=t.target.value;this._selected="__default__"===e?null:e,await this._loadViews()}async _onToggleUser(t,e){const s=t.visibleUserIds??this._users.map(t=>t.id),i=s.includes(e)?s.filter(t=>t!==e):[...s,e],o=i.length===this._users.length?[]:i;await((t,e,s,i)=>vt(t,{type:"ha_soc/permissions/view_visibility/set",url_path:e,view_path:s,user_ids:i}))(this.hass,this._selected??null,t.path,o),await this._loadViews()}async _onToggleFlag(t,e,s){await((t,e,s)=>vt(t,{type:"ha_soc/permissions/dashboard_flags/set",dashboard_id:e,...s}))(this.hass,t,{[e]:s}),await this._load()}async _onCheckDrift(){var t;this._drift=await(t=this.hass,vt(t,{type:"ha_soc/permissions/drift/check"}).then(t=>t.drift))}render(){if(this._loading)return j`<div class="empty">Loading dashboards…</div>`;const t=this._dashboards.find(t=>(t.url_path??null)===(this._selected??null));return j`
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
              `:B}
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._onCheckDrift}>Check drift</button>
        </div>

        ${this._drift.length?j`<p style="font-size:12.5px;color:var(--warning-color);">
              ${this._drift.length} view(s) no longer match the policy last applied here — likely edited directly in the dashboard editor.
            </p>`:B}

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
    `}};kt.styles=_t,t([pt({attribute:!1})],kt.prototype,"hass",void 0),t([ut()],kt.prototype,"_users",void 0),t([ut()],kt.prototype,"_dashboards",void 0),t([ut()],kt.prototype,"_selected",void 0),t([ut()],kt.prototype,"_views",void 0),t([ut()],kt.prototype,"_loading",void 0),t([ut()],kt.prototype,"_drift",void 0),kt=t([lt("ha-soc-permissions-view")],kt);const St=["new","confirmed","dismissed","resolved"];let Et=class extends nt{constructor(){super(...arguments),this._scannerFindings=[],this._vulnFindings=[],this._misconfigFindings=[],this._loading=!0,this._scanning=!1}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{const[e,s,i]=await Promise.all([(t=this.hass,vt(t,{type:"ha_soc/scanner/list"}).then(t=>t.findings)),mt(this.hass),$t(this.hass)]);this._scannerFindings=e,this._vulnFindings=s,this._misconfigFindings=i.misconfig_findings}finally{this._loading=!1}var t}async _onScanIntegrations(){this._scanning=!0;try{await(t=this.hass,vt(t,{type:"ha_soc/scanner/scan_now",domain:e})),await this._load()}finally{this._scanning=!1}var t,e}async _onScanVulns(){this._scanning=!0;try{await(t=this.hass,vt(t,{type:"ha_soc/vulns/scan_now"}).then(t=>t.findings)),await this._load()}finally{this._scanning=!1}var t}async _onVulnStatus(t,e){await((t,e,s,i)=>vt(t,{type:"ha_soc/vulns/set_status",finding_id:e,status:s,note:i}))(this.hass,t,e),await this._load()}async _onMisconfigStatus(t,e){await((t,e,s,i)=>vt(t,{type:"ha_soc/misconfig/set_status",finding_id:e,status:s,note:i}))(this.hass,t,e),await this._load()}_renderStatusSelect(t,e,s){return j`
      <select @change=${t=>s(t.target.value)}>
        ${St.map(t=>j`<option value=${t} ?selected=${t===e}>${t}</option>`)}
      </select>
    `}render(){return this._loading?j`<div class="empty">Loading findings…</div>`:j`
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
    `}};Et.styles=_t,t([pt({attribute:!1})],Et.prototype,"hass",void 0),t([ut()],Et.prototype,"_scannerFindings",void 0),t([ut()],Et.prototype,"_vulnFindings",void 0),t([ut()],Et.prototype,"_misconfigFindings",void 0),t([ut()],Et.prototype,"_loading",void 0),t([ut()],Et.prototype,"_scanning",void 0),Et=t([lt("ha-soc-scanner-view")],Et);let Ct=class extends nt{constructor(){super(...arguments),this._summary=null,this._detections=[],this._risk={},this._users=[],this._loading=!0}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{const[e,s,i,o]=await Promise.all([(t=this.hass,vt(t,{type:"ha_soc/dashboard/summary"})),bt(this.hass),yt(this.hass),gt(this.hass)]);this._summary=e,this._detections=s,this._risk=i,this._users=o}finally{this._loading=!1}var t}async _onAck(t){await ft(this.hass,t,"ack"),await this._load()}async _onResolve(t){await ft(this.hass,t,"resolved"),await this._load()}_nameFor(t){return t?this._users.find(e=>e.id===t)?.name??t:"unknown"}_donutGradient(t){const e=t.reduce((t,e)=>t+e.value,0)||1;let s=0;const i=t.map(t=>{const i=s/e*100;s+=t.value;const o=s/e*100;return`${t.color} ${i}% ${o}%`});return`conic-gradient(${i.join(", ")})`}render(){if(this._loading||!this._summary)return j`<div class="empty">Loading dashboard…</div>`;const t=this._summary,e=this._detections.filter(t=>"open"===t.status),s=[{key:"low",color:"var(--success-color, #43a047)"},{key:"moderate",color:"var(--warning-color, #ffa600)"},{key:"high",color:"#ec6a3a"},{key:"critical",color:"var(--error-color, #db4437)"}].map(e=>({...e,value:t.risk_band_counts[e.key]??0}));return j`
      <div class="tiles">
        <div class="tile">
          <div class="label">Security posture</div>
          <div class="value">${t.posture.score} <span style="font-size:14px;">(${t.posture.grade})</span></div>
        </div>
        <div class="tile">
          <div class="label">Open detections</div>
          <div class="value ${t.open_detections_count?"crit":""}">${t.open_detections_count}</div>
        </div>
        <div class="tile">
          <div class="label">Users at risk</div>
          <div class="value">${t.users_at_risk_count} <span style="font-size:14px;">of ${t.total_users_count}</span></div>
        </div>
        <div class="tile">
          <div class="label">Critical/high vulns</div>
          <div class="value">${t.critical_high_vuln_count}</div>
        </div>
      </div>

      <div class="donut-row">
        <div class="card">
          <h3>Users by risk band</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(s)}">
              <div class="center">${t.total_users_count}</div>
            </div>
            <div class="legend">
              ${s.map(t=>j`
                  <div class="row">
                    <span class="sw" style="background:${t.color}"></span>${t.key}
                    <span class="val">${t.value}</span>
                  </div>
                `)}
            </div>
          </div>
        </div>

        <div class="card">
          <h3>Posture breakdown</h3>
          <table>
            <tbody>
              ${Object.entries(t.posture.breakdown).map(([t,e])=>j`<tr><td>${t}</td><td class="muted">${e.toFixed(1)}</td></tr>`)}
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <h3>Recent suspicious activity</h3>
        ${e.length?j`
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
                  ${e.map(t=>j`
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
    `}};Ct.styles=[_t,r`
      .tiles {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .tile {
        background: var(--card-background-color, #fff);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0, 0, 0, 0.08));
        padding: 14px 16px;
      }
      .tile .label {
        font-size: 11px;
        text-transform: uppercase;
        color: var(--secondary-text-color);
        font-weight: 600;
      }
      .tile .value {
        font-size: 26px;
        font-weight: 700;
        margin-top: 4px;
      }
      .tile .value.crit {
        color: var(--error-color, #db4437);
      }
      .donut-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .donut-wrap {
        display: flex;
        align-items: center;
        gap: 14px;
      }
      .donut {
        width: 96px;
        height: 96px;
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
        font-size: 16px;
        z-index: 1;
      }
      .legend {
        font-size: 12px;
        display: flex;
        flex-direction: column;
        gap: 5px;
      }
      .legend .row {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .legend .sw {
        width: 8px;
        height: 8px;
        border-radius: 2px;
      }
      .legend .val {
        margin-left: auto;
        font-weight: 600;
      }
    `],t([pt({attribute:!1})],Ct.prototype,"hass",void 0),t([ut()],Ct.prototype,"_summary",void 0),t([ut()],Ct.prototype,"_detections",void 0),t([ut()],Ct.prototype,"_risk",void 0),t([ut()],Ct.prototype,"_users",void 0),t([ut()],Ct.prototype,"_loading",void 0),Ct=t([lt("ha-soc-dashboard-view")],Ct);const Ut=[{id:"dashboard",label:"Dashboard"},{id:"users",label:"Users & Access"},{id:"audit",label:"Audit Log"},{id:"permissions",label:"Permissions"},{id:"scanner",label:"Scanner"}];let Pt=class extends nt{constructor(){super(...arguments),this._tab="dashboard"}render(){return j`
      <div class="header">🛡️ HA SOC</div>
      <div class="tabs">
        ${Ut.map(t=>j`
            <div class="tab ${this._tab===t.id?"active":""}" @click=${()=>this._tab=t.id}>
              ${t.label}
            </div>
          `)}
      </div>
      ${this._renderTab()}
    `}_renderTab(){switch(this._tab){case"users":return j`<ha-soc-users-view .hass=${this.hass}></ha-soc-users-view>`;case"audit":return j`<ha-soc-audit-view .hass=${this.hass}></ha-soc-audit-view>`;case"permissions":return j`<ha-soc-permissions-view .hass=${this.hass}></ha-soc-permissions-view>`;case"scanner":return j`<ha-soc-scanner-view .hass=${this.hass}></ha-soc-scanner-view>`;default:return j`<ha-soc-dashboard-view .hass=${this.hass}></ha-soc-dashboard-view>`}}};Pt.styles=r`
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
  `,t([pt({attribute:!1})],Pt.prototype,"hass",void 0),t([pt({attribute:!1})],Pt.prototype,"narrow",void 0),t([pt({attribute:!1})],Pt.prototype,"panel",void 0),t([ut()],Pt.prototype,"_tab",void 0),Pt=t([lt("ha-soc-panel")],Pt);export{Pt as HaSocPanel};
