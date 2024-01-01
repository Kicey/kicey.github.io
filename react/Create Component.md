# Create Component

React App is made of components, all the components are managed in the root component.

The simplest way to create Root component:

```js
ReactDom.createRoot(document.getElementById("root"));
```

To create a custom(user defined or dom, document object model) component use the method (note that multiple children component  can passed):

```js
function createElement<P extends {}>(
        type: FunctionComponent<P> | ComponentClass<P> | string,
        props?: Attributes & P | null,
        ...children: ReactNode[]
): ReactElement<P>;
```

To define a custom component, if use `class`, extends the `React.Component` and access the props through `this.props.property_name`.

