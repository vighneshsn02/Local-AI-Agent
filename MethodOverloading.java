@author Your Name
public class MethodOverloading {
    public static void main(String[] args) {
        
        // Overloaded method 1: int add(int a, int b)
        int result1 = add(10, 20);
        System.out.println("Result of add(int, int): " + result1);

        // Overloaded method 2: double add(double a, double b)
        double result2 = add(10.5, 20.7);
        System.out.println("Result of add(double, double): " + result2);

        // Overloaded method 3: String concatenate(String a, String b)
        String result3 = concatenate("Hello, ", "world!");
        System.out.println("Result of concatenate(String, String): " + result3);
    }

    public static int add(int a, int b) {
        return a + b;
    }

    public static double add(double a, double b) {
        return a + b;
    }

    public static String concatenate(String a, String b) {
        return a + b;
    }
}