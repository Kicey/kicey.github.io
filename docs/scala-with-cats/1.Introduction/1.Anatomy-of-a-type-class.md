* A type class is an interface or API that represents some functionality we want to implement. In Scala a type class is represented by a trait with at least one type parameter.
  The trait `JsonWriter[A]` is a type class, `A` is the type parameter.

* The instances of a type class provide implementations of the type class for specific types we care about, which can include types from the Scala standard library and types from our domain model.
  The val `stringWriter` and `personWriter` are instances of `JsonWriter`, the specific types are `String` and `Person` here. One is from the Scala standard library and the other from the domain model.

* A type class use is any functionality that requires a type class instance to work. In Scala this means any method that accepts instances of the type class as implicit parameters.

  ```scala
  object Json:
    def toJson[A](value: A)(using w: JsonWriter[A]): Json =
      w.write(value)
  ```

  and

  ```scala
  object JsonSyntax:
    implicit class JsonWriterOps[A](value: A) :
      def toJson(implicit w: JsonWriter[A]): Json =
        w.write(value)
  ```

  are both type class uses.