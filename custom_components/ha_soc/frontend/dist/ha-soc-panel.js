function t(t,e,s,i){var a,o=arguments.length,r=o<3?e:null===i?i=Object.getOwnPropertyDescriptor(e,s):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)r=Reflect.decorate(t,e,s,i);else for(var n=t.length-1;n>=0;n--)(a=t[n])&&(r=(o<3?a(r):o>3?a(e,s,r):a(e,s))||r);return o>3&&r&&Object.defineProperty(e,s,r),r}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const e=globalThis,s=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,i=Symbol(),a=new WeakMap;let o=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==i)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(s&&void 0===t){const s=void 0!==e&&1===e.length;s&&(t=a.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&a.set(e,t))}return t}toString(){return this.cssText}};const r=(t,...e)=>{const s=1===t.length?t[0]:e.reduce((e,s,i)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+t[i+1],t[0]);return new o(s,t,i)},n=s?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const s of t.cssRules)e+=s.cssText;return(t=>new o("string"==typeof t?t:t+"",void 0,i))(e)})(t):t,{is:d,defineProperty:l,getOwnPropertyDescriptor:c,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,v=globalThis,g=v.trustedTypes,_=g?g.emptyScript:"",b=v.reactiveElementPolyfillSupport,y=(t,e)=>t,f={toAttribute(t,e){switch(e){case Boolean:t=t?_:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let s=t;switch(e){case Boolean:s=null!==t;break;case Number:s=null===t?null:Number(t);break;case Object:case Array:try{s=JSON.parse(t)}catch(t){s=null}}return s}},m=(t,e)=>!d(t,e),$={attribute:!0,type:String,converter:f,reflect:!1,useDefault:!1,hasChanged:m};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),v.litPropertyMetadata??=new WeakMap;let w=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=$){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const s=Symbol(),i=this.getPropertyDescriptor(t,s,e);void 0!==i&&l(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){const{get:i,set:a}=c(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:i,set(e){const o=i?.call(this);a?.call(this,e),this.requestUpdate(t,o,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??$}static _$Ei(){if(this.hasOwnProperty(y("elementProperties")))return;const t=u(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(y("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(y("properties"))){const t=this.properties,e=[...h(t),...p(t)];for(const s of e)this.createProperty(s,t[s])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,s]of e)this.elementProperties.set(t,s)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const s=this._$Eu(t,e);void 0!==s&&this._$Eh.set(s,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const s=new Set(t.flat(1/0).reverse());for(const t of s)e.unshift(n(t))}else void 0!==t&&e.push(n(t));return e}static _$Eu(t,e){const s=e.attribute;return!1===s?void 0:"string"==typeof s?s:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,i)=>{if(s)t.adoptedStyleSheets=i.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const s of i){const i=document.createElement("style"),a=e.litNonce;void 0!==a&&i.setAttribute("nonce",a),i.textContent=s.cssText,t.appendChild(i)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){const s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(void 0!==i&&!0===s.reflect){const a=(void 0!==s.converter?.toAttribute?s.converter:f).toAttribute(e,s.type);this._$Em=t,null==a?this.removeAttribute(i):this.setAttribute(i,a),this._$Em=null}}_$AK(t,e){const s=this.constructor,i=s._$Eh.get(t);if(void 0!==i&&this._$Em!==i){const t=s.getPropertyOptions(i),a="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:f;this._$Em=i;const o=a.fromAttribute(e,t.type);this[i]=o??this._$Ej?.get(i)??o,this._$Em=null}}requestUpdate(t,e,s,i=!1,a){if(void 0!==t){const o=this.constructor;if(!1===i&&(a=this[t]),s??=o.getPropertyOptions(t),!((s.hasChanged??m)(a,e)||s.useDefault&&s.reflect&&a===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,s))))return;this.C(t,e,s)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:a},o){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,o??e??this[t]),!0!==a||void 0!==o)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),!0===i&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,s]of t){const{wrapped:t}=s,i=this[e];!0!==t||this._$AL.has(e)||void 0===i||this.C(e,void 0,s,i)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};w.elementStyles=[],w.shadowRootOptions={mode:"open"},w[y("elementProperties")]=new Map,w[y("finalized")]=new Map,b?.({ReactiveElement:w}),(v.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const x=globalThis,k=t=>t,A=x.trustedTypes,S=A?A.createPolicy("lit-html",{createHTML:t=>t}):void 0,C="$lit$",E=`lit$${Math.random().toFixed(9).slice(2)}$`,U="?"+E,P=`<${U}>`,R=document,O=()=>R.createComment(""),M=t=>null===t||"object"!=typeof t&&"function"!=typeof t,N=Array.isArray,z="[ \t\n\f\r]",T=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,D=/-->/g,H=/>/g,V=RegExp(`>|${z}(?:([^\\s"'>=/]+)(${z}*=${z}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),L=/'/g,I=/"/g,F=/^(?:script|style|textarea|title)$/i,j=(t=>(e,...s)=>({_$litType$:t,strings:e,values:s}))(1),q=Symbol.for("lit-noChange"),B=Symbol.for("lit-nothing"),W=new WeakMap,G=R.createTreeWalker(R,129);function J(t,e){if(!N(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==S?S.createHTML(e):e}const K=(t,e)=>{const s=t.length-1,i=[];let a,o=2===e?"<svg>":3===e?"<math>":"",r=T;for(let e=0;e<s;e++){const s=t[e];let n,d,l=-1,c=0;for(;c<s.length&&(r.lastIndex=c,d=r.exec(s),null!==d);)c=r.lastIndex,r===T?"!--"===d[1]?r=D:void 0!==d[1]?r=H:void 0!==d[2]?(F.test(d[2])&&(a=RegExp("</"+d[2],"g")),r=V):void 0!==d[3]&&(r=V):r===V?">"===d[0]?(r=a??T,l=-1):void 0===d[1]?l=-2:(l=r.lastIndex-d[2].length,n=d[1],r=void 0===d[3]?V:'"'===d[3]?I:L):r===I||r===L?r=V:r===D||r===H?r=T:(r=V,a=void 0);const h=r===V&&t[e+1].startsWith("/>")?" ":"";o+=r===T?s+P:l>=0?(i.push(n),s.slice(0,l)+C+s.slice(l)+E+h):s+E+(-2===l?e:h)}return[J(t,o+(t[s]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),i]};class Y{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let a=0,o=0;const r=t.length-1,n=this.parts,[d,l]=K(t,e);if(this.el=Y.createElement(d,s),G.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(i=G.nextNode())&&n.length<r;){if(1===i.nodeType){if(i.hasAttributes())for(const t of i.getAttributeNames())if(t.endsWith(C)){const e=l[o++],s=i.getAttribute(t).split(E),r=/([.?@])?(.*)/.exec(e);n.push({type:1,index:a,name:r[2],strings:s,ctor:"."===r[1]?et:"?"===r[1]?st:"@"===r[1]?it:tt}),i.removeAttribute(t)}else t.startsWith(E)&&(n.push({type:6,index:a}),i.removeAttribute(t));if(F.test(i.tagName)){const t=i.textContent.split(E),e=t.length-1;if(e>0){i.textContent=A?A.emptyScript:"";for(let s=0;s<e;s++)i.append(t[s],O()),G.nextNode(),n.push({type:2,index:++a});i.append(t[e],O())}}}else if(8===i.nodeType)if(i.data===U)n.push({type:2,index:a});else{let t=-1;for(;-1!==(t=i.data.indexOf(E,t+1));)n.push({type:7,index:a}),t+=E.length-1}a++}}static createElement(t,e){const s=R.createElement("template");return s.innerHTML=t,s}}function Z(t,e,s=t,i){if(e===q)return e;let a=void 0!==i?s._$Co?.[i]:s._$Cl;const o=M(e)?void 0:e._$litDirective$;return a?.constructor!==o&&(a?._$AO?.(!1),void 0===o?a=void 0:(a=new o(t),a._$AT(t,s,i)),void 0!==i?(s._$Co??=[])[i]=a:s._$Cl=a),void 0!==a&&(e=Z(t,a._$AS(t,e.values),a,i)),e}class X{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??R).importNode(e,!0);G.currentNode=i;let a=G.nextNode(),o=0,r=0,n=s[0];for(;void 0!==n;){if(o===n.index){let e;2===n.type?e=new Q(a,a.nextSibling,this,t):1===n.type?e=new n.ctor(a,n.name,n.strings,this,t):6===n.type&&(e=new at(a,this,t)),this._$AV.push(e),n=s[++r]}o!==n?.index&&(a=G.nextNode(),o++)}return G.currentNode=R,i}p(t){let e=0;for(const s of this._$AV)void 0!==s&&(void 0!==s.strings?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}}class Q{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=B,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Z(this,t,e),M(t)?t===B||null==t||""===t?(this._$AH!==B&&this._$AR(),this._$AH=B):t!==this._$AH&&t!==q&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>N(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==B&&M(this._$AH)?this._$AA.nextSibling.data=t:this.T(R.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:s}=t,i="number"==typeof s?this._$AC(t):(void 0===s.el&&(s.el=Y.createElement(J(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{const t=new X(i,this),s=t.u(this.options);t.p(e),this.T(s),this._$AH=t}}_$AC(t){let e=W.get(t.strings);return void 0===e&&W.set(t.strings,e=new Y(t)),e}k(t){N(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let s,i=0;for(const a of t)i===e.length?e.push(s=new Q(this.O(O()),this.O(O()),this,this.options)):s=e[i],s._$AI(a),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=k(t).nextSibling;k(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class tt{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,a){this.type=1,this._$AH=B,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=a,s.length>2||""!==s[0]||""!==s[1]?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=B}_$AI(t,e=this,s,i){const a=this.strings;let o=!1;if(void 0===a)t=Z(this,t,e,0),o=!M(t)||t!==this._$AH&&t!==q,o&&(this._$AH=t);else{const i=t;let r,n;for(t=a[0],r=0;r<a.length-1;r++)n=Z(this,i[s+r],e,r),n===q&&(n=this._$AH[r]),o||=!M(n)||n!==this._$AH[r],n===B?t=B:t!==B&&(t+=(n??"")+a[r+1]),this._$AH[r]=n}o&&!i&&this.j(t)}j(t){t===B?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class et extends tt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===B?void 0:t}}class st extends tt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==B)}}class it extends tt{constructor(t,e,s,i,a){super(t,e,s,i,a),this.type=5}_$AI(t,e=this){if((t=Z(this,t,e,0)??B)===q)return;const s=this._$AH,i=t===B&&s!==B||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,a=t!==B&&(s===B||i);i&&this.element.removeEventListener(this.name,this,s),a&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class at{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){Z(this,t)}}const ot=x.litHtmlPolyfillSupport;ot?.(Y,Q),(x.litHtmlVersions??=[]).push("3.3.3");const rt=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class nt extends w{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,s)=>{const i=s?.renderBefore??e;let a=i._$litPart$;if(void 0===a){const t=s?.renderBefore??null;i._$litPart$=a=new Q(e.insertBefore(O(),t),t,void 0,s??{})}return a._$AI(t),a})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return q}}nt._$litElement$=!0,nt.finalized=!0,rt.litElementHydrateSupport?.({LitElement:nt});const dt=rt.litElementPolyfillSupport;dt?.({LitElement:nt}),(rt.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const lt=t=>(e,s)=>{void 0!==s?s.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},ct={attribute:!0,type:String,converter:f,reflect:!1,hasChanged:m},ht=(t=ct,e,s)=>{const{kind:i,metadata:a}=s;let o=globalThis.litPropertyMetadata.get(a);if(void 0===o&&globalThis.litPropertyMetadata.set(a,o=new Map),"setter"===i&&((t=Object.create(t)).wrapped=!0),o.set(s.name,t),"accessor"===i){const{name:i}=s;return{set(s){const a=e.get.call(this);e.set.call(this,s),this.requestUpdate(i,a,t,!0,s)},init(e){return void 0!==e&&this.C(i,void 0,t,e),e}}}if("setter"===i){const{name:i}=s;return function(s){const a=this[i];e.call(this,s),this.requestUpdate(i,a,t,!0,s)}}throw Error("Unsupported decorator location: "+i)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function pt(t){return(e,s)=>"object"==typeof s?ht(t,e,s):((t,e,s)=>{const i=e.hasOwnProperty(s);return e.constructor.createProperty(s,t),i?Object.getOwnPropertyDescriptor(e,s):void 0})(t,e,s)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ut(t){return pt({...t,state:!0,attribute:!1})}const vt=r`
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
`,gt=(t,e)=>t.callWS(e),_t=t=>gt(t,{type:"ha_soc/users/list"}).then(t=>t.users),bt=t=>gt(t,{type:"ha_soc/risk/list"}).then(t=>t.risk),yt=(t,e)=>gt(t,{type:"ha_soc/detections/list",status:e}).then(t=>t.detections),ft=(t,e,s)=>gt(t,{type:"ha_soc/detections/set_status",detection_id:e,status:s}),mt=t=>gt(t,{type:"ha_soc/vulns/list"}).then(t=>t.findings),$t=t=>gt(t,{type:"ha_soc/health/list"}),wt=t=>gt(t,{type:"ha_soc/dashboard/nodes"});let xt=class extends nt{constructor(){super(...arguments),this._users=[],this._risk={},this._loading=!0,this._busyUserId=null}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{const[t,e]=await Promise.all([_t(this.hass),bt(this.hass)]);this._users=t,this._risk=e}finally{this._loading=!1}}_fmtDate(t){if(!t)return"never";return new Date(t).toLocaleString()}async _onDeactivate(t){if(confirm("Deactivate this user? All their sessions will be revoked.")){this._busyUserId=t;try{await((t,e)=>gt(t,{type:"ha_soc/users/deactivate",user_id:e}))(this.hass,t),await this._load()}finally{this._busyUserId=null}}}async _onRevokeAll(t){if(confirm("Revoke every interactive session for this user? Long-lived tokens are kept.")){this._busyUserId=t;try{await((t,e)=>gt(t,{type:"ha_soc/users/revoke_all_sessions",user_id:e}))(this.hass,t),await this._load()}finally{this._busyUserId=null}}}async _onResetPassword(t){const e=prompt("New password for this user (owner-only action):");if(e){this._busyUserId=t;try{const s=await((t,e,s)=>gt(t,{type:"ha_soc/users/set_password",user_id:e,password:s}))(this.hass,t,e);s&&!1===s.ok&&alert("Could not set password — only the account owner can reset another user's password.")}finally{this._busyUserId=null}}}render(){return this._loading?j`<div class="empty">Loading users…</div>`:this._users.length?j`
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
    `:j`<div class="empty">No users found.</div>`}};xt.styles=vt,t([pt({attribute:!1})],xt.prototype,"hass",void 0),t([ut()],xt.prototype,"_users",void 0),t([ut()],xt.prototype,"_risk",void 0),t([ut()],xt.prototype,"_loading",void 0),t([ut()],xt.prototype,"_busyUserId",void 0),xt=t([lt("ha-soc-users-view")],xt);const kt=["","service_call","login_ok","login_fail","token_created","user_added","user_updated","user_removed","lovelace_change","entity_registry_change"];let At=class extends nt{constructor(){super(...arguments),this._events=[],this._loading=!0,this._category="",this._verifyResult=null}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{this._events=await((t,e={})=>gt(t,{type:"ha_soc/audit/query",...e}).then(t=>t.events))(this.hass,{category:this._category||void 0,limit:200})}finally{this._loading=!1}}async _onVerify(){var t;this._verifyResult=await(t=this.hass,gt(t,{type:"ha_soc/audit/verify_chain"}))}_onCategoryChange(t){this._category=t.target.value,this._load()}render(){return j`
      <div class="card">
        <h3>Audit Log</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Every user-attributed service call, user/dashboard change, and
          best-effort login signal. Failed logins carry only a source IP — Home
          Assistant never logs the attempted username on a failed login.
        </p>
        <div class="toolbar">
          <select @change=${this._onCategoryChange}>
            ${kt.map(t=>j`<option value=${t} ?selected=${t===this._category}>${t||"All categories"}</option>`)}
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
    `}};At.styles=vt,t([pt({attribute:!1})],At.prototype,"hass",void 0),t([ut()],At.prototype,"_events",void 0),t([ut()],At.prototype,"_loading",void 0),t([ut()],At.prototype,"_category",void 0),t([ut()],At.prototype,"_verifyResult",void 0),At=t([lt("ha-soc-audit-view")],At);let St=class extends nt{constructor(){super(...arguments),this._users=[],this._dashboards=[],this._selected=void 0,this._views=[],this._loading=!0,this._drift=[]}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{const[e,s]=await Promise.all([_t(this.hass),(t=this.hass,gt(t,{type:"ha_soc/permissions/dashboards/list"}).then(t=>t.dashboards))]);this._users=e.filter(t=>t.is_active),this._dashboards=s,void 0===this._selected&&s.length&&(this._selected=s[0].url_path??null),void 0!==this._selected&&await this._loadViews()}finally{this._loading=!1}var t}async _loadViews(){const t=await(e=this.hass,s=this._selected??null,gt(e,{type:"ha_soc/permissions/dashboard_config",url_path:s}).then(t=>t.config));var e,s;const i=t?.views??[];this._views=i.map((t,e)=>({path:t.path??String(e),title:t.title??t.path??`View ${e+1}`,visibleUserIds:Array.isArray(t.visible)?t.visible.map(t=>t.user):null}))}async _onSelectDashboard(t){const e=t.target.value;this._selected="__default__"===e?null:e,await this._loadViews()}async _onToggleUser(t,e){const s=t.visibleUserIds??this._users.map(t=>t.id),i=s.includes(e)?s.filter(t=>t!==e):[...s,e],a=i.length===this._users.length?[]:i;await((t,e,s,i)=>gt(t,{type:"ha_soc/permissions/view_visibility/set",url_path:e,view_path:s,user_ids:i}))(this.hass,this._selected??null,t.path,a),await this._loadViews()}async _onToggleFlag(t,e,s){await((t,e,s)=>gt(t,{type:"ha_soc/permissions/dashboard_flags/set",dashboard_id:e,...s}))(this.hass,t,{[e]:s}),await this._load()}async _onCheckDrift(){var t;this._drift=await(t=this.hass,gt(t,{type:"ha_soc/permissions/drift/check"}).then(t=>t.drift))}render(){if(this._loading)return j`<div class="empty">Loading dashboards…</div>`;const t=this._dashboards.find(t=>(t.url_path??null)===(this._selected??null));return j`
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
    `}};St.styles=vt,t([pt({attribute:!1})],St.prototype,"hass",void 0),t([ut()],St.prototype,"_users",void 0),t([ut()],St.prototype,"_dashboards",void 0),t([ut()],St.prototype,"_selected",void 0),t([ut()],St.prototype,"_views",void 0),t([ut()],St.prototype,"_loading",void 0),t([ut()],St.prototype,"_drift",void 0),St=t([lt("ha-soc-permissions-view")],St);const Ct=["new","confirmed","dismissed","resolved"];let Et=class extends nt{constructor(){super(...arguments),this._scannerFindings=[],this._vulnFindings=[],this._misconfigFindings=[],this._loading=!0,this._scanning=!1}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{const[e,s,i]=await Promise.all([(t=this.hass,gt(t,{type:"ha_soc/scanner/list"}).then(t=>t.findings)),mt(this.hass),$t(this.hass)]);this._scannerFindings=e,this._vulnFindings=s,this._misconfigFindings=i.misconfig_findings}finally{this._loading=!1}var t}async _onScanIntegrations(){this._scanning=!0;try{await(t=this.hass,gt(t,{type:"ha_soc/scanner/scan_now",domain:e})),await this._load()}finally{this._scanning=!1}var t,e}async _onScanVulns(){this._scanning=!0;try{await(t=this.hass,gt(t,{type:"ha_soc/vulns/scan_now"}).then(t=>t.findings)),await this._load()}finally{this._scanning=!1}var t}async _onVulnStatus(t,e){await((t,e,s,i)=>gt(t,{type:"ha_soc/vulns/set_status",finding_id:e,status:s,note:i}))(this.hass,t,e),await this._load()}async _onMisconfigStatus(t,e){await((t,e,s,i)=>gt(t,{type:"ha_soc/misconfig/set_status",finding_id:e,status:s,note:i}))(this.hass,t,e),await this._load()}_renderStatusSelect(t,e,s){return j`
      <select @change=${t=>s(t.target.value)}>
        ${Ct.map(t=>j`<option value=${t} ?selected=${t===e}>${t}</option>`)}
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
    `}};Et.styles=vt,t([pt({attribute:!1})],Et.prototype,"hass",void 0),t([ut()],Et.prototype,"_scannerFindings",void 0),t([ut()],Et.prototype,"_vulnFindings",void 0),t([ut()],Et.prototype,"_misconfigFindings",void 0),t([ut()],Et.prototype,"_loading",void 0),t([ut()],Et.prototype,"_scanning",void 0),Et=t([lt("ha-soc-scanner-view")],Et);const Ut=[{key:"up",label:"Up"},{key:"warning",label:"Warning"},{key:"critical",label:"Critical"},{key:"down",label:"Down"},{key:"unmanaged",label:"Unmanaged"},{key:"other",label:"Other"}],Pt=["critical","high","medium","low"];let Rt=class extends nt{constructor(){super(...arguments),this._summary=null,this._nodeOverview=null,this._detections=[],this._risk={},this._users=[],this._loading=!0,this._nodeSearch="",this._nodeSort={key:"risk_score",dir:"desc"}}connectedCallback(){super.connectedCallback(),this._load()}updated(){this.classList.toggle("dark",!!this.hass?.themes?.darkMode)}async _load(){this._loading=!0;try{const[e,s,i,a,o]=await Promise.all([(t=this.hass,gt(t,{type:"ha_soc/dashboard/summary"})),wt(this.hass),yt(this.hass),bt(this.hass),_t(this.hass)]);this._summary=e,this._nodeOverview=s,this._detections=i,this._risk=a,this._users=o}finally{this._loading=!1}var t}async _onAck(t){await ft(this.hass,t,"ack"),await this._load()}async _onResolve(t){await ft(this.hass,t,"resolved"),await this._load()}_nameFor(t){return t?this._users.find(e=>e.id===t)?.name??t:"unknown"}_goto(t){!function(t,e){t.dispatchEvent(new CustomEvent("ha-soc-navigate",{detail:{tab:e},bubbles:!0,composed:!0}))}(this,t)}_donutGradient(t){const e=t.reduce((t,e)=>t+e.value,0)||1;let s=0;const i=t.map(t=>{const i=s/e*100;s+=t.value;const a=s/e*100;return`${t.color} ${i}% ${a}%`});return`conic-gradient(${i.join(", ")})`}_onSort(t){this._nodeSort=this._nodeSort.key===t?{key:t,dir:"asc"===this._nodeSort.dir?"desc":"asc"}:{key:t,dir:"name"===t||"vendor"===t?"asc":"desc"}}_sortedFilteredNodes(){const t=this._nodeOverview?.nodes??[],e=this._nodeSearch.trim().toLowerCase(),s=e?t.filter(t=>t.name.toLowerCase().includes(e)||t.vendor.toLowerCase().includes(e)||t.os.toLowerCase().includes(e)):t,{key:i,dir:a}=this._nodeSort,o=[...s].sort((t,e)=>{const s=t[i],o=e[i],r="string"==typeof s?s.localeCompare(o):s-o;return"asc"===a?r:-r});return o}_statusDotColor(t){switch(t){case"critical":return"var(--status-serious)";case"down":return"var(--status-critical)";case"warning":return"var(--status-warning)";case"unmanaged":return"var(--primary-color)";case"other":return"var(--cat-other)";default:return"var(--status-good)"}}render(){if(this._loading||!this._summary||!this._nodeOverview)return j`<div class="empty">Loading dashboard…</div>`;const t=this._summary,e=this._nodeOverview,s=this._detections.filter(t=>"open"===t.status),i=e.nodes.reduce((t,e)=>(t.critical+=e.severity_counts.critical,t.high+=e.severity_counts.high,t.medium+=e.severity_counts.medium,t.low+=e.severity_counts.low,t),{critical:0,high:0,medium:0,low:0}),a=i.critical+i.high+i.medium+i.low,o=[{key:"critical",label:"Critical",color:"var(--status-critical)",value:i.critical},{key:"high",label:"High",color:"var(--status-serious)",value:i.high},{key:"medium",label:"Medium",color:"var(--status-warning)",value:i.medium},{key:"low",label:"Low",color:"var(--status-good)",value:i.low}],r=Math.max(0,Math.min(100,e.combined_risk_score/10*100)),n=Object.entries(e.by_vendor).sort((t,e)=>e[1]-t[1]),d=["--cat-1","--cat-2","--cat-3","--cat-4","--cat-5","--cat-6","--cat-7","--cat-8"],l=n.slice(0,8),c=n.slice(8).reduce((t,[,e])=>t+e,0),h=c>0?[...l,["Other",c]]:l,p=Math.max(1,...h.map(([,t])=>t)),u=[{key:"low",color:"var(--status-good)",value:t.risk_band_counts.low??0},{key:"moderate",color:"var(--status-warning)",value:t.risk_band_counts.moderate??0},{key:"high",color:"var(--status-serious)",value:t.risk_band_counts.high??0},{key:"critical",color:"var(--status-critical)",value:t.risk_band_counts.critical??0}],v=[{key:"enabled",color:"var(--cat-1)",value:t.mfa_counts.enabled},{key:"disabled",color:"var(--cat-2)",value:t.mfa_counts.disabled}],g=[{key:"critical",color:"var(--status-critical)",value:t.detection_severity_counts.critical??0},{key:"high",color:"var(--status-serious)",value:t.detection_severity_counts.high??0},{key:"medium",color:"var(--status-warning)",value:t.detection_severity_counts.medium??0},{key:"low",color:"var(--status-good)",value:t.detection_severity_counts.low??0}];return j`
      <h2 class="section-title">Device &amp; Vulnerability Overview</h2>
      <div class="row3">
        <div class="card">
          <h3>Node Status</h3>
          <div class="status-tiles">
            ${Ut.map(t=>j`
                <div
                  class="status-tile clickable ${t.key}"
                  title="View in Scanner"
                  @click=${()=>this._goto("scanner")}
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
            <div class="donut" style="background:${this._donutGradient(o)}">
              <div class="center">${a.toLocaleString()}</div>
            </div>
            <div class="legend">
              ${o.map(t=>j`
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
            Combined risk score of all nodes — weighted so higher-severity CVEs count more.
          </div>
        </div>
      </div>

      <div class="row2">
        <div class="card">
          <h3>All Nodes</h3>
          <div class="nodes-toolbar">
            <input
              type="text"
              placeholder="Search nodes…"
              .value=${this._nodeSearch}
              @input=${t=>this._nodeSearch=t.target.value}
            />
          </div>
          ${0===this._sortedFilteredNodes().length?j`<div class="empty">No devices found.</div>`:j`
                <div style="overflow-x:auto;">
                  <table>
                    <thead>
                      <tr>
                        <th>Health</th>
                        <th class="sortable" @click=${()=>this._onSort("name")}>
                          Node${this._sortArrow("name")}
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
                      ${this._sortedFilteredNodes().map(t=>j`
                          <tr class="clickable" @click=${()=>this._goto("scanner")}>
                            <td><span class="health-dot" style="background:${this._statusDotColor(t.status)}"></span></td>
                            <td>${t.name}</td>
                            <td class="muted">${t.vendor}</td>
                            <td class="num">${t.risk_score.toFixed(1)}</td>
                            <td class="num">${t.total_findings}</td>
                            <td>
                              <span class="sev-cell">
                                ${Pt.map(e=>j`
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
              `}
        </div>

        <div class="card clickable" @click=${()=>this._goto("scanner")} title="View vulnerability findings">
          <h3>Vulnerability Count by OS</h3>
          ${0===h.length?j`<div class="empty">No findings yet.</div>`:j`
                <div class="vbar-chart">
                  ${h.map(([t,e],s)=>j`
                      <div class="vbar-col">
                        <div class="vbar-value">${e}</div>
                        <div class="vbar-fill" style="height:${e/p*100}%; background:${"Other"===t?"var(--cat-other)":`var(${d[s%d.length]})`};"></div>
                        <div class="vbar-label" title=${t}>${t}</div>
                      </div>
                    `)}
                </div>
              `}
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

      <div class="card">
        <h3>Recent suspicious activity</h3>
        ${s.length?j`
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
                  ${s.map(t=>j`
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
    `}_sortArrow(t){return this._nodeSort.key!==t?B:j`<span class="arrow">${"asc"===this._nodeSort.dir?"▲":"▼"}</span>`}};Rt.styles=[vt,r`
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
        grid-template-columns: 1.3fr 1fr 1fr;
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
      .status-tiles {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 8px;
      }
      .status-tile {
        border-radius: 10px;
        padding: 10px 6px;
        text-align: center;
        background: var(--card-background-color, #fff);
        border: 1px solid var(--divider-color);
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
      .status-tile.warning {
        background: var(--status-warning);
        color: #3a2900;
      }
      .status-tile.critical {
        background: var(--status-serious);
        color: #fff;
      }
      .status-tile.down {
        background: var(--status-critical);
        color: #fff;
      }
      .status-tile.unmanaged {
        background: var(--primary-color);
        color: #fff;
      }
      .status-tile.other {
        background: var(--cat-other);
        color: #fff;
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

      /* -- All Nodes table --------------------------------------------------- */
      .nodes-toolbar {
        display: flex;
        gap: 8px;
        margin-bottom: 10px;
      }
      .nodes-toolbar input {
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

      /* -- Vertical bar chart (vulns by OS/vendor) ---------------------------- */
      .vbar-chart {
        display: flex;
        align-items: flex-end;
        gap: 10px;
        height: 200px;
        padding-top: 20px;
      }
      .vbar-col {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-end;
        height: 100%;
        min-width: 0;
      }
      .vbar-col .vbar-value {
        font-size: 11px;
        font-weight: 700;
        margin-bottom: 4px;
        font-variant-numeric: tabular-nums;
      }
      .vbar-col .vbar-fill {
        width: 60%;
        border-radius: 4px 4px 0 0;
        min-height: 2px;
      }
      .vbar-col .vbar-label {
        font-size: 10.5px;
        color: var(--secondary-text-color);
        margin-top: 6px;
        text-align: center;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 100%;
      }
    `],t([pt({attribute:!1})],Rt.prototype,"hass",void 0),t([ut()],Rt.prototype,"_summary",void 0),t([ut()],Rt.prototype,"_nodeOverview",void 0),t([ut()],Rt.prototype,"_detections",void 0),t([ut()],Rt.prototype,"_risk",void 0),t([ut()],Rt.prototype,"_users",void 0),t([ut()],Rt.prototype,"_loading",void 0),t([ut()],Rt.prototype,"_nodeSearch",void 0),t([ut()],Rt.prototype,"_nodeSort",void 0),Rt=t([lt("ha-soc-dashboard-view")],Rt);const Ot=[{id:"dashboard",label:"Dashboard"},{id:"users",label:"Users & Access"},{id:"audit",label:"Audit Log"},{id:"permissions",label:"Permissions"},{id:"scanner",label:"Scanner"}];let Mt=class extends nt{constructor(){super(...arguments),this._tab="dashboard"}render(){return j`
      <div class="header">🛡️ HA SOC</div>
      <div class="tabs">
        ${Ot.map(t=>j`
            <div class="tab ${this._tab===t.id?"active":""}" @click=${()=>this._tab=t.id}>
              ${t.label}
            </div>
          `)}
      </div>
      <div @ha-soc-navigate=${this._onNavigate}>${this._renderTab()}</div>
    `}_onNavigate(t){this._tab=t.detail.tab}_renderTab(){switch(this._tab){case"users":return j`<ha-soc-users-view .hass=${this.hass}></ha-soc-users-view>`;case"audit":return j`<ha-soc-audit-view .hass=${this.hass}></ha-soc-audit-view>`;case"permissions":return j`<ha-soc-permissions-view .hass=${this.hass}></ha-soc-permissions-view>`;case"scanner":return j`<ha-soc-scanner-view .hass=${this.hass}></ha-soc-scanner-view>`;default:return j`<ha-soc-dashboard-view .hass=${this.hass}></ha-soc-dashboard-view>`}}};Mt.styles=r`
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
  `,t([pt({attribute:!1})],Mt.prototype,"hass",void 0),t([pt({attribute:!1})],Mt.prototype,"narrow",void 0),t([pt({attribute:!1})],Mt.prototype,"panel",void 0),t([ut()],Mt.prototype,"_tab",void 0),Mt=t([lt("ha-soc-panel")],Mt);export{Mt as HaSocPanel};
