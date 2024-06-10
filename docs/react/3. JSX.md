# JSX

Instead of create custom components by `Root.createElement`, we can use JSX to crate react component.

There are three parameters needed to create a react component: `type`, `properties`, `children`, they passed to the JSX through the type of the dom element, element properties and the children element:

```jsx
<CustomComponent props = {props}>
    {shoudHasChild && <Child childProps = {childProps}></Child>}
</CustomComponent>
```

And, can use some operator like `&&` whin the `{}`, just like the JSX component is a variable. So that, the JSX can also create from a stream using `map`, which generates a list of JSX component.

Note, that here is a special prop: `key` react use that to identify a component, which means that there will only render one component for each different key.